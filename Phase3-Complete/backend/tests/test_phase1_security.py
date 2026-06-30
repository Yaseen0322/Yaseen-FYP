import asyncio
import unittest
import os
import tempfile

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.crypto import encrypt_json_payload
from app.core.database import Base, get_db
from app.core.security import create_access_token, create_oauth_state, get_password_hash
from app.main import app
from app.models.alerts import Alert
from app.models.device import Device
from app.models.integrations import Integration, SSOProvider
from app.models.organization import Organization
from app.models.user import User


class Phase1SecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="phase1-security-", suffix=".db")
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

    def _create_org(self, name="Org"):
        db = self.SessionLocal()
        org = Organization(name=name)
        db.add(org)
        db.commit()
        db.refresh(org)
        db.close()
        return org

    def _create_user(self, org_id, email, role="employee", password="password123", is_active=True):
        db = self.SessionLocal()
        user = User(
            org_id=org_id,
            email=email,
            name=email.split("@")[0],
            hashed_password=get_password_hash(password),
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

    def _request(self, method, url, **kwargs):
        async def do_request():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver"
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(do_request())

    def test_manager_cannot_create_manager_account(self):
        org = self._create_org("Org One")
        manager = self._create_user(org.id, "manager@example.com", role="manager")

        response = self._request(
            "POST",
            "/api/v1/users/",
            json={
                "email": "new-manager@example.com",
                "name": "New Manager",
                "password": "password123",
                "role": "manager",
            },
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("permission", response.json()["detail"].lower())

    def test_manager_user_list_hides_admin_accounts(self):
        org = self._create_org("Org One")
        manager = self._create_user(org.id, "manager@example.com", role="manager")
        self._create_user(org.id, "employee@example.com", role="employee")
        self._create_user(org.id, "admin@example.com", role="admin")

        response = self._request(
            "GET",
            "/api/v1/users/",
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        roles = {item["role"] for item in response.json()["items"]}
        self.assertEqual(roles, {"employee"})

    def test_alert_read_is_scoped_to_org(self):
        org_one = self._create_org("Org One")
        org_two = self._create_org("Org Two")
        manager = self._create_user(org_one.id, "manager@example.com", role="manager")
        employee = self._create_user(org_two.id, "employee@example.com", role="employee")

        db = self.SessionLocal()
        alert = Alert(
            org_id=org_two.id,
            user_id=employee.id,
            alert_type="low_productivity",
            severity="medium",
            title="Cross org alert",
            message="Should not be readable",
            context_json={},
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        db.close()

        response = self._request(
            "POST",
            f"/api/v1/alerts/{alert.id}/read",
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 404)

    def test_device_registration_rejects_machine_hijack(self):
        org = self._create_org("Org One")
        user_one = self._create_user(org.id, "one@example.com")
        user_two = self._create_user(org.id, "two@example.com")

        db = self.SessionLocal()
        device = Device(
            user_id=user_one.id,
            machine_id="shared-machine",
            hostname="host-a",
            os="linux",
            os_version="1",
            is_active=True,
        )
        db.add(device)
        db.commit()
        db.close()

        response = self._request(
            "POST",
            "/api/v1/devices/register",
            json={
                "machine_id": "shared-machine",
                "hostname": "host-b",
                "os": "linux",
                "os_version": "2",
                "app_version": "1.0.0",
            },
            headers=self._headers_for(user_two.id),
        )

        self.assertEqual(response.status_code, 409)

    def test_google_login_rejects_unconfigured_redirect_uri(self):
        org = self._create_org("Org One")

        db = self.SessionLocal()
        provider = SSOProvider(
            org_id=org.id,
            provider_type="google",
            name="Google Workspace",
            is_active=True,
            config_json=encrypt_json_payload(
                {
                    "client_id": "google-client",
                    "client_secret": "google-secret",
                    "redirect_uri": "https://portal.example.com/google/callback",
                }
            ),
        )
        db.add(provider)
        db.commit()
        db.close()

        response = self._request(
            "GET",
            "/api/v1/sso/google/login",
            params={
                "org_id": org.id,
                "redirect_uri": "https://evil.example.com/google/callback",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("redirect", response.json()["detail"].lower())

    def test_google_callback_rejects_tampered_state(self):
        org = self._create_org("Org One")

        db = self.SessionLocal()
        provider = SSOProvider(
            org_id=org.id,
            provider_type="google",
            name="Google Workspace",
            is_active=True,
            config_json=encrypt_json_payload(
                {
                    "client_id": "google-client",
                    "client_secret": "google-secret",
                    "redirect_uri": "https://portal.example.com/google/callback",
                }
            ),
        )
        db.add(provider)
        db.commit()
        db.close()

        state = create_oauth_state(
            provider="google",
            org_id=org.id,
            redirect_uri="https://portal.example.com/google/callback",
            code_verifier="verifier",
        )

        response = self._request(
            "GET",
            "/api/v1/sso/google/callback",
            params={
                "code": "dummy-code",
                "state": state,
                "redirect_uri": "https://evil.example.com/google/callback",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("redirect", response.json()["detail"].lower())

    def test_integration_config_is_encrypted_at_rest(self):
        org = self._create_org("Org One")
        admin = self._create_user(org.id, "admin@example.com", role="admin")

        response = self._request(
            "POST",
            "/api/v1/integrations/",
            json={
                "integration_type": "slack",
                "name": "Slack Alerts",
                "config_json": {
                    "webhook_url": "https://hooks.slack.test/services/abc"
                },
            },
            headers=self._headers_for(admin.id),
        )

        self.assertEqual(response.status_code, 200)

        db = self.SessionLocal()
        integration = db.query(Integration).filter(Integration.org_id == org.id).one()
        db.close()

        self.assertTrue(integration.config_json.get("__encrypted__"))
        self.assertNotIn("webhook_url", integration.config_json)


if __name__ == "__main__":
    unittest.main()
