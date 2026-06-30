import asyncio
import os
import tempfile
import unittest
from datetime import date, datetime, time
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.crypto import encrypt_json_payload
from app.core.database import Base, get_db
from app.core.dates import utc_today
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.alerts import Alert, AlertRule
from app.models.daily_summary import DailySummary
from app.models.device import Device
from app.models.integrations import Integration, SSOProvider
from app.models.organization import Organization
from app.models.user import User
from app.services.alert_processor import AlertProcessor
from app.services.runtime_jobs import process_org_alerts


class PhaseERuntimeFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="phasee-runtime-", suffix=".db")
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

    def _create_device(self, user_id, machine_id="device-1"):
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

    def _dt(self, target_day: date, hour: int, minute: int):
        return datetime.combine(target_day, time(hour=hour, minute=minute))

    def test_browser_ingest_creates_pending_ml_classification(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com")
        device = self._create_device(employee.id)
        target_day = date.today()

        ingest_response = self._request(
            "POST",
            "/api/v1/ingest/browser-usage",
            json={
                "items": [
                    {
                        "device_id": device.id,
                        "browser": "Chrome",
                        "domain": "coursera.org",
                        "start_ts": self._dt(target_day, 9, 0).isoformat(),
                        "end_ts": self._dt(target_day, 9, 10).isoformat(),
                        "duration_sec": 600,
                    }
                ]
            },
            headers=self._headers_for(employee.id),
        )

        self.assertEqual(ingest_response.status_code, 200)

        response = self._request(
            "GET",
            "/api/v1/ml/classifications",
            params={"status": "pending", "limit": 10, "offset": 0},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["classification_type"], "domain")
        self.assertEqual(payload["items"][0]["input_value"], "coursera.org")
        self.assertEqual(payload["items"][0]["predicted_label"], "productive")

    def test_app_usage_ingest_creates_pending_app_classification(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com")
        device = self._create_device(employee.id)
        target_day = date.today()

        ingest_response = self._request(
            "POST",
            "/api/v1/ingest/app-usage",
            json={
                "items": [
                    {
                        "device_id": device.id,
                        "app_name": "Visual Studio Code",
                        "window_title": "main.py",
                        "start_ts": self._dt(target_day, 10, 0).isoformat(),
                        "end_ts": self._dt(target_day, 10, 15).isoformat(),
                        "duration_sec": 900,
                    }
                ]
            },
            headers=self._headers_for(employee.id),
        )

        self.assertEqual(ingest_response.status_code, 200)

        response = self._request(
            "GET",
            "/api/v1/ml/classifications",
            params={"status": "pending", "limit": 10, "offset": 0},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["classification_type"], "app")
        self.assertEqual(payload["items"][0]["predicted_label"], "productive")

    def test_alert_processing_endpoint_creates_alerts_from_daily_summary(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com")
        target_day = utc_today()

        db = self.SessionLocal()
        db.add(AlertRule(
            org_id=org.id,
            name="Idle spike",
            alert_type="excessive_idle",
            severity="high",
            config_json={"threshold_seconds": 7200},
            is_active=True,
            notify_manager=True,
        ))
        db.add(DailySummary(
            user_id=employee.id,
            date=target_day,
            idle_sec=7500,
            focus_sec=1200,
        ))
        db.commit()
        db.close()

        with patch("app.services.alert_processor.utc_today", return_value=target_day):
            first_response = self._request(
                "POST",
                "/api/v1/alerts/process",
                headers=self._headers_for(manager.id),
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.json()["created_count"], 1)
        self.assertEqual(first_response.json()["slack_sent"], 0)

        with patch("app.services.alert_processor.utc_today", return_value=target_day):
            second_response = self._request(
                "POST",
                "/api/v1/alerts/process",
                headers=self._headers_for(manager.id),
            )

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["created_count"], 0)

        db = self.SessionLocal()
        alerts = db.query(Alert).filter(Alert.org_id == org.id).all()
        db.close()
        self.assertEqual(len(alerts), 1)

    def test_alert_processing_endpoint_uses_utc_operational_day(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com")
        target_day = date(2026, 1, 5)

        db = self.SessionLocal()
        db.add(AlertRule(
            org_id=org.id,
            name="Idle spike",
            alert_type="excessive_idle",
            severity="high",
            config_json={"threshold_seconds": 60},
            is_active=True,
            notify_manager=False,
        ))
        db.add(DailySummary(
            user_id=employee.id,
            date=target_day,
            idle_sec=120,
            focus_sec=600,
        ))
        db.commit()
        db.close()

        with patch("app.services.alert_processor.utc_today", return_value=target_day):
            response = self._request(
                "POST",
                "/api/v1/alerts/process",
                headers=self._headers_for(manager.id),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created_count"], 1)

    def test_process_org_alerts_attempts_slack_delivery_when_configured(self):
        org = self._create_org()
        employee = self._create_user(org.id, "employee@example.com")
        target_day = utc_today()

        db = self.SessionLocal()
        db.add(AlertRule(
            org_id=org.id,
            name="Camera off",
            alert_type="camera_off_long",
            severity="medium",
            config_json={"threshold_seconds": 3600},
            is_active=True,
            notify_manager=True,
        ))
        db.add(DailySummary(
            user_id=employee.id,
            date=target_day,
            camera_off_sec=3700,
        ))
        db.add(Integration(
            org_id=org.id,
            integration_type="slack",
            name="Slack alerts",
            config_json=encrypt_json_payload({"webhook_url": "https://hooks.slack.test/services/abc"}),
            is_active=True,
            is_configured=True,
        ))
        db.commit()

        with patch("app.services.slack_notifier.SlackNotifier.send_alert_notification", new=AsyncMock(return_value=True)) as mocked_send:
            with patch("app.services.alert_processor.utc_today", return_value=target_day):
                result = asyncio.run(process_org_alerts(db, org.id))

        db.close()
        self.assertEqual(result["created_count"], 1)
        self.assertEqual(result["slack_sent"], 1)
        self.assertEqual(mocked_send.await_count, 1)

    def test_alert_processor_is_idempotent_even_if_precheck_misses_existing_alert(self):
        org = self._create_org()
        employee = self._create_user(org.id, "employee@example.com")

        db = self.SessionLocal()
        rule = AlertRule(
            org_id=org.id,
            name="Idle spike",
            alert_type="excessive_idle",
            severity="high",
            config_json={"threshold_seconds": 7200},
            is_active=True,
            notify_manager=True,
        )
        db.add(rule)
        db.flush()
        db.add(DailySummary(
            user_id=employee.id,
            date=date.today(),
            idle_sec=7500,
        ))
        db.add(Alert(
            org_id=org.id,
            user_id=employee.id,
            rule_id=rule.id,
            alert_type="excessive_idle",
            severity="high",
            title="Existing alert",
            message="Already created",
            context_json={"date": date.today().isoformat()},
            dedupe_key=f"{org.id}:{employee.id}:excessive_idle:{date.today().isoformat()}",
        ))
        db.commit()

        processor = AlertProcessor(db)
        with patch.object(processor, "_get_existing_alert_user_ids", return_value=set()):
            created = processor.process_all_rules(org.id, target_date=date.today())
        db.commit()

        alerts = db.query(Alert).filter(Alert.org_id == org.id).all()
        db.close()

        self.assertEqual(created, [])
        self.assertEqual(len(alerts), 1)

    def test_ingest_to_summary_to_alert_path(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com")
        device = self._create_device(employee.id)
        target_day = utc_today()

        db = self.SessionLocal()
        db.add(AlertRule(
            org_id=org.id,
            name="Idle spike",
            alert_type="excessive_idle",
            severity="high",
            config_json={"threshold_seconds": 3600},
            is_active=True,
            notify_manager=True,
        ))
        db.commit()
        db.close()

        ingest_response = self._request(
            "POST",
            "/api/v1/ingest/idle-intervals",
            json={
                "items": [
                    {
                        "device_id": device.id,
                        "start_ts": self._dt(target_day, 9, 0).isoformat(),
                        "end_ts": self._dt(target_day, 10, 30).isoformat(),
                        "duration_sec": 5400,
                    }
                ]
            },
            headers=self._headers_for(employee.id),
        )
        self.assertEqual(ingest_response.status_code, 200)

        summary_response = self._request(
            "GET",
            "/api/v1/me/summary",
            params={"target_date": target_day.isoformat()},
            headers=self._headers_for(employee.id),
        )
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["idle_sec"], 5400)

        with patch("app.services.alert_processor.utc_today", return_value=target_day):
            process_response = self._request(
                "POST",
                "/api/v1/alerts/process",
                headers=self._headers_for(manager.id),
            )
        self.assertEqual(process_response.status_code, 200)
        self.assertEqual(process_response.json()["created_count"], 1)

        alerts_response = self._request(
            "GET",
            "/api/v1/alerts/",
            headers=self._headers_for(manager.id),
        )
        self.assertEqual(alerts_response.status_code, 200)
        self.assertEqual(alerts_response.json()["total"], 1)
        self.assertEqual(alerts_response.json()["items"][0]["alert_type"], "excessive_idle")

    def test_integration_detail_and_sso_update_flow(self):
        org = self._create_org()
        admin = self._create_user(org.id, "admin@example.com", role="admin")

        db = self.SessionLocal()
        integration = Integration(
            org_id=org.id,
            integration_type="jira",
            name="Jira",
            config_json=encrypt_json_payload(
                {
                    "api_url": "https://example.atlassian.net",
                    "email": "jira@example.com",
                    "api_token": "secret-token",
                }
            ),
            is_configured=True,
        )
        provider = SSOProvider(
            org_id=org.id,
            provider_type="google",
            name="Google Workspace",
            config_json=encrypt_json_payload(
                {
                    "client_id": "client-1",
                    "client_secret": "secret-1",
                    "redirect_uri": "https://portal.example.com/google/callback",
                }
            ),
        )
        db.add(integration)
        db.add(provider)
        db.commit()
        db.refresh(integration)
        db.refresh(provider)
        integration_id = integration.id
        provider_id = provider.id
        db.close()

        integration_detail = self._request(
            "GET",
            f"/api/v1/integrations/{integration_id}",
            headers=self._headers_for(admin.id),
        )
        self.assertEqual(integration_detail.status_code, 200)
        self.assertEqual(integration_detail.json()["config_json"]["api_url"], "https://example.atlassian.net")

        integration_update = self._request(
            "PATCH",
            f"/api/v1/integrations/{integration_id}",
            json={
                "name": "Jira Prod",
                "config_json": {
                    "api_url": "https://prod.atlassian.net",
                    "email": "jira@example.com",
                    "api_token": "new-secret-token",
                },
            },
            headers=self._headers_for(admin.id),
        )
        self.assertEqual(integration_update.status_code, 200)

        provider_update = self._request(
            "PATCH",
            f"/api/v1/integrations/sso/{provider_id}",
            json={
                "name": "Google Main",
                "config_json": {
                    "client_id": "client-1",
                    "client_secret": "secret-2",
                    "redirect_uri": "https://portal.example.com/google/callback",
                },
            },
            headers=self._headers_for(admin.id),
        )
        self.assertEqual(provider_update.status_code, 200)

        delete_response = self._request(
            "DELETE",
            f"/api/v1/integrations/sso/{provider_id}",
            headers=self._headers_for(admin.id),
        )
        self.assertEqual(delete_response.status_code, 200)

    def test_integration_validation_rejects_unsupported_type(self):
        org = self._create_org()
        admin = self._create_user(org.id, "admin@example.com", role="admin")

        response = self._request(
            "POST",
            "/api/v1/integrations/",
            json={
                "integration_type": "microsoft_teams",
                "name": "Teams",
                "config_json": {},
            },
            headers=self._headers_for(admin.id),
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
