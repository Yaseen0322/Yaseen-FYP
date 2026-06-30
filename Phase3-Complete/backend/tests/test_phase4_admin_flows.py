import asyncio
import os
import tempfile
import unittest

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.browser_usage import DomainRule
from app.models.organization import Department, Organization
from app.models.user import User


class Phase4AdminFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="phase4-admin-", suffix=".db")
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

    def _create_user(self, org_id, email, role="admin", dept_id=None):
        db = self.SessionLocal()
        user = User(
            org_id=org_id,
            email=email,
            name=email.split("@")[0],
            hashed_password=get_password_hash("password123"),
            role=role,
            dept_id=dept_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    def _headers_for(self, user_id):
        token = create_access_token({"sub": str(user_id)})
        return {"Authorization": f"Bearer {token}"}

    def test_department_delete_requires_reassignment(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")

        db = self.SessionLocal()
        dept = Department(org_id=org.id, name="Engineering", description="Core product")
        db.add(dept)
        db.commit()
        db.refresh(dept)
        db.close()

        self._create_user(org.id, "employee@example.com", role="employee", dept_id=dept.id)

        response = self._request(
            "DELETE",
            f"/api/v1/org/departments/{dept.id}",
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("reassign", response.json()["detail"].lower())

    def test_department_can_be_updated(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")

        db = self.SessionLocal()
        dept = Department(org_id=org.id, name="Engineering", description="Core product")
        db.add(dept)
        db.commit()
        db.refresh(dept)
        db.close()

        response = self._request(
            "PATCH",
            f"/api/v1/org/departments/{dept.id}",
            json={"name": "Platform", "description": "Shared services"},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Platform")
        self.assertEqual(response.json()["description"], "Shared services")

    def test_domain_rule_can_be_updated(self):
        org = self._create_org()
        manager = self._create_user(org.id, "manager@example.com", role="manager")

        db = self.SessionLocal()
        rule = DomainRule(
            org_id=org.id,
            domain="example.com",
            category="General",
            label="neutral",
            dept_overrides_json={},
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        db.close()

        response = self._request(
            "PATCH",
            f"/api/v1/manager/domain-rules/{rule.id}",
            json={"category": "Development", "label": "productive"},
            headers=self._headers_for(manager.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["category"], "Development")
        self.assertEqual(response.json()["label"], "productive")


if __name__ == "__main__":
    unittest.main()
