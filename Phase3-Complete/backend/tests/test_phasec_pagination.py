import asyncio
import os
import tempfile
import unittest
from datetime import date, datetime, time

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.crypto import encrypt_json_payload
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.alerts import Alert
from app.models.activity import AppUsage
from app.models.device import Device
from app.models.integrations import Integration, SSOProvider
from app.models.organization import Organization
from app.models.user import User


class PhaseCPaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="phasec-pagination-", suffix=".db")
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

    def _create_user(self, org_id, email, role="employee", is_active=True):
        db = self.SessionLocal()
        user = User(
            org_id=org_id,
            email=email,
            name=email.split("@")[0],
            hashed_password=get_password_hash("password123"),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    def _headers_for(self, user_id):
        token = create_access_token({"sub": str(user_id)})
        return {"Authorization": f"Bearer {token}"}

    def _dt(self, target_day: date, hour: int, minute: int):
        return datetime.combine(target_day, time(hour=hour, minute=minute))

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

    def test_users_endpoint_returns_paginated_shape(self):
        org = self._create_org()
        admin = self._create_user(org.id, "admin@example.com", role="admin")
        for idx in range(5):
            self._create_user(org.id, f"user{idx}@example.com", role="employee")

        response = self._request(
            "GET",
            "/api/v1/users/",
            params={"limit": 2, "offset": 1},
            headers=self._headers_for(admin.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["offset"], 1)
        self.assertEqual(payload["total"], 6)
        self.assertEqual(len(payload["items"]), 2)

    def test_alerts_endpoint_returns_paginated_shape(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com", role="employee")

        db = self.SessionLocal()
        for idx in range(4):
            db.add(Alert(
                org_id=org.id,
                user_id=employee.id,
                alert_type="low_productivity",
                severity="medium",
                title=f"Alert {idx}",
                message="Check activity",
                context_json={},
            ))
        db.commit()
        db.close()

        response = self._request(
            "GET",
            "/api/v1/alerts/",
            params={"limit": 2, "offset": 1},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 4)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["offset"], 1)

    def test_integrations_endpoint_returns_paginated_shape(self):
        org = self._create_org()
        admin = self._create_user(org.id, "admin@example.com", role="admin")

        db = self.SessionLocal()
        for idx in range(3):
            db.add(Integration(
                org_id=org.id,
                integration_type="slack",
                name=f"Slack {idx}",
                config_json=encrypt_json_payload({"webhook_url": f"https://hooks.test/{idx}"}),
                is_configured=True,
            ))
        for idx in range(2):
            db.add(SSOProvider(
                org_id=org.id,
                provider_type="google",
                name=f"Google {idx}",
                config_json=encrypt_json_payload({"client_id": f"client-{idx}", "redirect_uri": f"https://app.test/{idx}"}),
            ))
        db.commit()
        db.close()

        integrations = self._request(
            "GET",
            "/api/v1/integrations/",
            params={"limit": 2, "offset": 1},
            headers=self._headers_for(admin.id),
        )
        providers = self._request(
            "GET",
            "/api/v1/integrations/sso",
            params={"limit": 1, "offset": 1},
            headers=self._headers_for(admin.id),
        )

        self.assertEqual(integrations.status_code, 200)
        self.assertEqual(integrations.json()["total"], 3)
        self.assertEqual(len(integrations.json()["items"]), 2)

        self.assertEqual(providers.status_code, 200)
        self.assertEqual(providers.json()["total"], 2)
        self.assertEqual(len(providers.json()["items"]), 1)

    def test_employee_timeline_returns_paginated_blocks(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        employee = self._create_user(org.id, "employee@example.com", role="employee")
        device = self._create_device(employee.id)

        target_day = date.today()
        db = self.SessionLocal()
        for idx in range(3):
            db.add(AppUsage(
                user_id=employee.id,
                device_id=device.id,
                app_name=f"App {idx}",
                window_title=f"Window {idx}",
                start_ts=self._dt(target_day, 9 + idx, 0),
                end_ts=self._dt(target_day, 9 + idx, 10),
                duration_sec=600,
            ))
        db.commit()
        db.close()

        response = self._request(
            "GET",
            f"/api/v1/manager/employees/{employee.id}/timeline",
            params={"target_date": target_day.isoformat(), "limit": 2, "offset": 1},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["limit"], 2)
        self.assertEqual(payload["offset"], 1)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["type"], "app_usage")
        self.assertEqual(payload["items"][0]["details"]["app_name"], "App 1")


if __name__ == "__main__":
    unittest.main()
