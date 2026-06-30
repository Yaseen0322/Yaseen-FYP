import asyncio
import os
import tempfile
import unittest
from datetime import date, datetime, time, timedelta

import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.activity import AppUsage
from app.models.daily_summary import DailySummary
from app.models.device import Device
from app.models.organization import Department, Organization
from app.models.user import User


class PhaseDAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="phased-analytics-", suffix=".db")
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

    def _create_org(self):
        db = self.SessionLocal()
        org = Organization(name="Org")
        db.add(org)
        db.commit()
        db.refresh(org)
        db.close()
        return org

    def _create_department(self, org_id, name):
        db = self.SessionLocal()
        dept = Department(org_id=org_id, name=name)
        db.add(dept)
        db.commit()
        db.refresh(dept)
        db.close()
        return dept

    def _create_user(self, org_id, dept_id, email, role="employee"):
        db = self.SessionLocal()
        user = User(
            org_id=org_id,
            dept_id=dept_id,
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

    def _create_device(self, user_id):
        db = self.SessionLocal()
        device = Device(
            user_id=user_id,
            machine_id=f"machine-{user_id}",
            hostname=f"host-{user_id}",
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

    def _dt(self, target_day: date, hour: int, minute: int):
        return datetime.combine(target_day, time(hour=hour, minute=minute))

    def test_department_summary_uses_grouped_query_and_returns_correct_totals(self):
        org = self._create_org()
        dept_a = self._create_department(org.id, "Engineering")
        dept_b = self._create_department(org.id, "Support")
        manager = self._create_user(org.id, dept_a.id, "manager@example.com", role="manager")
        user_a1 = self._create_user(org.id, dept_a.id, "a1@example.com")
        user_a2 = self._create_user(org.id, dept_a.id, "a2@example.com")
        user_b1 = self._create_user(org.id, dept_b.id, "b1@example.com")

        target_day = date.today()
        db = self.SessionLocal()
        db.add_all([
            DailySummary(user_id=user_a1.id, date=target_day, focus_sec=600, present_sec=900, idle_sec=60, productive_sec=500, unproductive_sec=100),
            DailySummary(user_id=user_a2.id, date=target_day, focus_sec=300, present_sec=600, idle_sec=120, productive_sec=200, unproductive_sec=100),
            DailySummary(user_id=user_b1.id, date=target_day, focus_sec=120, present_sec=300, idle_sec=30, productive_sec=60, unproductive_sec=60),
        ])
        db.commit()
        db.close()

        query_count = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal query_count
            if statement.lstrip().upper().startswith("SELECT"):
                query_count += 1

        event.listen(self.engine, "before_cursor_execute", before_cursor_execute)
        try:
          response = self._request(
              "GET",
              "/api/v1/analytics/departments/summary",
              params={"target_date": target_day.isoformat()},
              headers=self._headers_for(manager.id),
          )
        finally:
          event.remove(self.engine, "before_cursor_execute", before_cursor_execute)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertLessEqual(query_count, 3)

        engineering = next(item for item in payload["departments"] if item["department"]["name"] == "Engineering")
        self.assertEqual(engineering["employee_count"], 2)
        self.assertEqual(engineering["total_focus_sec"], 900)
        self.assertEqual(engineering["avg_focus_sec"], 450)
        self.assertEqual(engineering["productivity_ratio"], 77.8)

    def test_department_details_and_trends_use_summary_data(self):
        org = self._create_org()
        dept = self._create_department(org.id, "Engineering")
        manager = self._create_user(org.id, dept.id, "manager@example.com", role="manager")
        user_one = self._create_user(org.id, dept.id, "one@example.com")
        user_two = self._create_user(org.id, dept.id, "two@example.com")
        device = self._create_device(user_one.id)

        target_day = date.today()
        week_start = target_day - timedelta(days=target_day.weekday())
        comparison_day = week_start if week_start != target_day else week_start + timedelta(days=1)

        db = self.SessionLocal()
        db.add_all([
            DailySummary(user_id=user_one.id, date=target_day, focus_sec=600, present_sec=700, idle_sec=60, productive_sec=500),
            DailySummary(user_id=user_two.id, date=target_day, focus_sec=300, present_sec=400, idle_sec=90, productive_sec=200),
            DailySummary(user_id=user_one.id, date=comparison_day, focus_sec=240, present_sec=360, idle_sec=30, productive_sec=180),
            DailySummary(user_id=user_two.id, date=comparison_day, focus_sec=120, present_sec=180, idle_sec=15, productive_sec=60),
            AppUsage(
                user_id=user_one.id,
                device_id=device.id,
                app_name="VS Code",
                window_title="main.py",
                start_ts=self._dt(target_day, 10, 0),
                end_ts=self._dt(target_day, 10, 15),
                duration_sec=900,
            ),
        ])
        db.commit()
        db.close()

        details = self._request(
            "GET",
            f"/api/v1/analytics/departments/{dept.id}/details",
            params={"target_date": target_day.isoformat(), "limit": 1, "offset": 0},
            headers=self._headers_for(manager.id),
        )
        trends = self._request(
            "GET",
            "/api/v1/analytics/trends/weekly",
            params={"dept_id": dept.id},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(details.status_code, 200)
        detail_payload = details.json()
        self.assertEqual(detail_payload["employees_total"], 2)
        self.assertEqual(detail_payload["employees_limit"], 1)
        self.assertEqual(len(detail_payload["employees"]), 1)
        self.assertEqual(detail_payload["employees"][0]["focus_sec"], 600)
        self.assertEqual(detail_payload["top_apps"][0]["app_name"], "VS Code")

        self.assertEqual(trends.status_code, 200)
        trend_payload = trends.json()
        today_row = next(item for item in trend_payload["trends"] if item["date"] == target_day.isoformat())
        comparison_row = next(item for item in trend_payload["trends"] if item["date"] == comparison_day.isoformat())
        self.assertEqual(today_row["avg_focus_sec"], 450)
        self.assertEqual(comparison_row["avg_focus_sec"], 180)


if __name__ == "__main__":
    unittest.main()
