import asyncio
import os
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.activity import AppUsage, IdleInterval
from app.models.browser_usage import BrowserUsage
from app.models.daily_summary import DailySummary
from app.models.device import Device
from app.models.organization import Organization
from app.models.presence import PresenceInterval
from app.models.user import User


class Phase2ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="phase2-reporting-", suffix=".db")
        os.close(fd)
        cls.engine = create_engine(
            f"sqlite:///{cls.db_path}",
            connect_args={"check_same_thread": False},
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        async def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        if os.path.exists(cls.db_path):
            os.unlink(cls.db_path)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def _request(self, method, url, **kwargs):
        async def do_request():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(do_request())

    def _create_org(self, name="Org"):
        db = self.SessionLocal()
        org = Organization(name=name)
        db.add(org)
        db.commit()
        db.refresh(org)
        db.close()
        return org

    def _create_user(self, org_id, email, role="employee"):
        db = self.SessionLocal()
        user = User(
            org_id=org_id,
            email=email,
            name=email.split("@")[0],
            hashed_password=get_password_hash("password123"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    def _create_device(self, user_id, machine_id="machine-1"):
        db = self.SessionLocal()
        device = Device(
            user_id=user_id,
            machine_id=machine_id,
            hostname=machine_id,
            os="linux",
            os_version="1.0",
            is_active=True,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        db.close()
        return device

    def _headers_for(self, user_id):
        token = create_access_token({"sub": str(user_id)})
        return {"Authorization": f"Bearer {token}"}

    def _dt(self, target_day: date, hour: int, minute: int, second: int = 0):
        return datetime.combine(target_day, time(hour=hour, minute=minute, second=second))

    def test_summary_clips_midnight_and_subtracts_idle(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)

        target_day = date.today() - timedelta(days=1)
        previous_day = target_day - timedelta(days=1)
        # Records are stored as UTC by the desktop agent. PKT midnight for
        # target_day is 19:00 UTC on previous_day.

        db = self.SessionLocal()
        db.add(AppUsage(
            user_id=user.id,
            device_id=device.id,
            app_name="VS Code",
            window_title="main.py",
            start_ts=self._dt(previous_day, 18, 50),
            end_ts=self._dt(previous_day, 19, 10),
            duration_sec=20 * 60,
        ))
        db.add(IdleInterval(
            user_id=user.id,
            device_id=device.id,
            start_ts=self._dt(previous_day, 19, 5),
            end_ts=self._dt(previous_day, 19, 8),
            duration_sec=3 * 60,
        ))
        db.add(PresenceInterval(
            user_id=user.id,
            device_id=device.id,
            state="present",
            start_ts=self._dt(previous_day, 18, 55),
            end_ts=self._dt(previous_day, 19, 15),
            duration_sec=20 * 60,
        ))
        db.add(BrowserUsage(
            user_id=user.id,
            device_id=device.id,
            browser="Chrome",
            domain="github.com",
            start_ts=self._dt(previous_day, 18, 58),
            end_ts=self._dt(previous_day, 19, 4),
            duration_sec=6 * 60,
            category="Development/Work",
            label="productive",
        ))
        db.commit()
        db.close()

        response = self._request(
            "GET",
            "/api/v1/me/summary",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(user.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["focus_sec"], 7 * 60)
        self.assertEqual(payload["idle_sec"], 3 * 60)
        self.assertEqual(payload["present_sec"], 15 * 60)
        self.assertEqual(payload["productive_sec"], 7 * 60)
        self.assertEqual(payload["top_apps"][0]["duration_sec"], 10 * 60)
        self.assertEqual(payload["top_domains"][0]["duration_sec"], 4 * 60)

    def test_timeline_clips_cross_midnight_intervals(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)

        target_day = date.today() - timedelta(days=1)
        previous_day = target_day - timedelta(days=1)
        # PKT midnight for target_day is 19:00 UTC on previous_day.

        db = self.SessionLocal()
        db.add(AppUsage(
            user_id=user.id,
            device_id=device.id,
            app_name="Terminal",
            window_title="shell",
            start_ts=self._dt(previous_day, 18, 55),
            end_ts=self._dt(previous_day, 19, 5),
            duration_sec=10 * 60,
        ))
        db.commit()
        db.close()

        response = self._request(
            "GET",
            "/api/v1/me/timeline",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(user.id),
        )

        self.assertEqual(response.status_code, 200)
        blocks = response.json()["blocks"]
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["duration_sec"], 5 * 60)
        self.assertTrue(blocks[0]["start_ts"].startswith(f"{target_day.isoformat()}T00:00:00"))
        self.assertTrue(blocks[0]["start_ts"].endswith("+05:00"))

    def test_ingest_rejects_mixed_device_batch(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device_one = self._create_device(user.id, "device-1")
        device_two = self._create_device(user.id, "device-2")

        target_day = date.today()
        response = self._request(
            "POST",
            "/api/v1/ingest/app-usage",
            json={
                "items": [
                    {
                        "device_id": device_one.id,
                        "app_name": "VS Code",
                        "window_title": "app.py",
                        "start_ts": self._dt(target_day, 10, 0).isoformat(),
                        "end_ts": self._dt(target_day, 10, 10).isoformat(),
                        "duration_sec": 600,
                    },
                    {
                        "device_id": device_two.id,
                        "app_name": "Chrome",
                        "window_title": "Docs",
                        "start_ts": self._dt(target_day, 10, 10).isoformat(),
                        "end_ts": self._dt(target_day, 10, 20).isoformat(),
                        "duration_sec": 600,
                    },
                ]
            },
            headers=self._headers_for(user.id),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("same device_id", response.json()["detail"])

    def test_ingest_rejects_invalid_duration(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)

        target_day = date.today()
        response = self._request(
            "POST",
            "/api/v1/ingest/idle-intervals",
            json={
                "items": [
                    {
                        "device_id": device.id,
                        "start_ts": self._dt(target_day, 9, 0).isoformat(),
                        "end_ts": self._dt(target_day, 9, 5).isoformat(),
                        "duration_sec": 120,
                    }
                ]
            },
            headers=self._headers_for(user.id),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("duration_sec", response.json()["detail"])

    def test_ingest_refreshes_historical_daily_summary(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)

        target_day = date.today() - timedelta(days=2)
        response = self._request(
            "POST",
            "/api/v1/ingest/app-usage",
            json={
                "items": [
                    {
                        "device_id": device.id,
                        "app_name": "VS Code",
                        "window_title": "report.py",
                        "start_ts": self._dt(target_day, 11, 0).isoformat(),
                        "end_ts": self._dt(target_day, 11, 10).isoformat(),
                        "duration_sec": 600,
                    }
                ]
            },
            headers=self._headers_for(user.id),
        )

        self.assertEqual(response.status_code, 200)

        db = self.SessionLocal()
        summary = db.query(DailySummary).filter(
            DailySummary.user_id == user.id,
            DailySummary.date == target_day,
        ).first()
        db.close()

        self.assertIsNotNone(summary)
        self.assertEqual(summary.focus_sec, 600)

        summary_response = self._request(
            "GET",
            "/api/v1/me/summary",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(user.id),
        )

        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["focus_sec"], 600)

    def test_summary_defaults_to_utc_day(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)
        target_day = date(2026, 1, 5)

        db = self.SessionLocal()
        db.add(AppUsage(
            user_id=user.id,
            device_id=device.id,
            app_name="VS Code",
            window_title="utc-demo.py",
            start_ts=self._dt(target_day, 9, 0),
            end_ts=self._dt(target_day, 9, 10),
            duration_sec=600,
        ))
        db.commit()
        db.close()

        with patch("app.api.reports.utc_today", return_value=target_day):
            response = self._request(
                "GET",
                "/api/v1/me/summary",
                headers=self._headers_for(user.id),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["date"], target_day.isoformat())
        self.assertEqual(response.json()["focus_sec"], 600)

    def test_ingest_is_idempotent_for_idle_and_browser_usage(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)
        target_day = date.today()

        idle_payload = {
            "items": [
                {
                    "device_id": device.id,
                    "start_ts": self._dt(target_day, 10, 0).isoformat(),
                    "end_ts": self._dt(target_day, 10, 2).isoformat(),
                    "duration_sec": 120,
                }
            ]
        }
        browser_payload = {
            "items": [
                {
                    "device_id": device.id,
                    "browser": "Chrome",
                    "domain": "www.youtube.com",
                    "start_ts": self._dt(target_day, 10, 5).isoformat(),
                    "end_ts": self._dt(target_day, 10, 8).isoformat(),
                    "duration_sec": 180,
                }
            ]
        }

        for _ in range(2):
            idle_response = self._request(
                "POST",
                "/api/v1/ingest/idle-intervals",
                json=idle_payload,
                headers=self._headers_for(user.id),
            )
            browser_response = self._request(
                "POST",
                "/api/v1/ingest/browser-usage",
                json=browser_payload,
                headers=self._headers_for(user.id),
            )
            self.assertEqual(idle_response.status_code, 200)
            self.assertEqual(browser_response.status_code, 200)

        db = self.SessionLocal()
        idle_count = db.query(IdleInterval).filter(IdleInterval.user_id == user.id).count()
        browser_rows = db.query(BrowserUsage).filter(BrowserUsage.user_id == user.id).all()
        db.close()

        self.assertEqual(idle_count, 1)
        self.assertEqual(len(browser_rows), 1)
        self.assertEqual(browser_rows[0].domain, "youtube.com")
        self.assertEqual(browser_rows[0].label, "unproductive")

        summary_response = self._request(
            "GET",
            "/api/v1/me/summary",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(user.id),
        )
        summary = summary_response.json()
        self.assertEqual(summary["idle_sec"], 120)
        self.assertEqual(summary["top_domains"][0]["domain"], "youtube.com")
        self.assertEqual(summary["top_domains"][0]["duration_sec"], 180)

        timeline_response = self._request(
            "GET",
            "/api/v1/me/timeline",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(user.id),
        )
        blocks = timeline_response.json()["blocks"]
        self.assertEqual(len([block for block in blocks if block["type"] == "idle"]), 1)
        self.assertEqual(len([block for block in blocks if block["type"] == "browser_usage"]), 1)

    def test_timeline_coalesces_contiguous_tracking_chunks(self):
        org = self._create_org()
        user = self._create_user(org.id, "employee@example.com")
        device = self._create_device(user.id)
        target_day = date.today()

        db = self.SessionLocal()
        db.add_all([
            IdleInterval(
                user_id=user.id,
                device_id=device.id,
                start_ts=self._dt(target_day, 10, 0),
                end_ts=self._dt(target_day, 10, 1),
                duration_sec=60,
            ),
            IdleInterval(
                user_id=user.id,
                device_id=device.id,
                start_ts=self._dt(target_day, 10, 1),
                end_ts=self._dt(target_day, 10, 2),
                duration_sec=60,
            ),
            BrowserUsage(
                user_id=user.id,
                device_id=device.id,
                browser="Chrome",
                domain="youtube.com",
                start_ts=self._dt(target_day, 10, 5),
                end_ts=self._dt(target_day, 10, 6),
                duration_sec=60,
                category="Social/Entertainment",
                label="unproductive",
            ),
            BrowserUsage(
                user_id=user.id,
                device_id=device.id,
                browser="Chrome",
                domain="youtube.com",
                start_ts=self._dt(target_day, 10, 6),
                end_ts=self._dt(target_day, 10, 8),
                duration_sec=120,
                category="Social/Entertainment",
                label="unproductive",
            ),
            PresenceInterval(
                user_id=user.id,
                device_id=device.id,
                state="camera_off",
                start_ts=self._dt(target_day, 10, 0),
                end_ts=self._dt(target_day, 10, 1),
                duration_sec=60,
            ),
            PresenceInterval(
                user_id=user.id,
                device_id=device.id,
                state="present",
                start_ts=self._dt(target_day, 10, 1),
                end_ts=self._dt(target_day, 10, 3),
                duration_sec=120,
            ),
        ])
        db.commit()
        db.close()

        response = self._request(
            "GET",
            "/api/v1/me/timeline",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(user.id),
        )

        self.assertEqual(response.status_code, 200)
        blocks = response.json()["blocks"]
        idle_blocks = [block for block in blocks if block["type"] == "idle"]
        browser_blocks = [block for block in blocks if block["type"] == "browser_usage"]
        self.assertEqual(len(idle_blocks), 1)
        self.assertEqual(idle_blocks[0]["duration_sec"], 120)
        self.assertEqual(len(browser_blocks), 1)
        self.assertEqual(browser_blocks[0]["duration_sec"], 180)
        self.assertEqual(len([block for block in blocks if block["type"] == "camera_off"]), 1)
        self.assertEqual(len([block for block in blocks if block["type"] == "present"]), 1)


if __name__ == "__main__":
    unittest.main()
