"""
Seed demo manager and employee accounts for the local Phase 3 demo database.

Run with DATABASE_URL pointing at the intended database, for example:
DATABASE_URL=sqlite:///./demo_staging.db python scripts/seed_demo_accounts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import get_password_hash
from app.core.database import SessionLocal
from app.models.organization import Department, Organization
from app.models.user import User


DEMO_PASSWORD = "Password@123"

DEMO_USERS = [
    {
        "email": "manager@Yaseenfyp.com",
        "name": "Demo Manager",
        "employee_id": "MGR-001",
        "role": "manager",
    },
    {
        "email": "employee1@Yaseenfyp.com",
        "name": "Demo Employee One",
        "employee_id": "EMP-001",
        "role": "employee",
    },
    {
        "email": "employee2@Yaseenfyp.com",
        "name": "Demo Employee Two",
        "employee_id": "EMP-002",
        "role": "employee",
    },
]


def get_or_create_org(db):
    org = db.query(Organization).order_by(Organization.id.asc()).first()
    if org:
        return org

    org = Organization(
        name="Yaseen FYP Demo Organization",
        timezone="Asia/Karachi",
        retention_days=90,
        is_active=True,
    )
    db.add(org)
    db.flush()
    return org


def get_or_create_department(db, org_id):
    dept = db.query(Department).filter(
        Department.org_id == org_id,
        Department.name == "Engineering",
    ).first()
    if dept:
        return dept

    dept = Department(
        org_id=org_id,
        name="Engineering",
        description="Demo software engineering department",
    )
    db.add(dept)
    db.flush()
    return dept


def upsert_user(db, org_id, dept_id, user_data):
    user = db.query(User).filter(User.email == user_data["email"]).first()
    password_hash = get_password_hash(DEMO_PASSWORD)

    if user:
        user.org_id = org_id
        user.dept_id = dept_id
        user.name = user_data["name"]
        user.employee_id = user_data["employee_id"]
        user.role = user_data["role"]
        user.status = "active"
        user.is_active = True
        user.hashed_password = password_hash
        return user

    user = User(
        org_id=org_id,
        dept_id=dept_id,
        email=user_data["email"],
        name=user_data["name"],
        employee_id=user_data["employee_id"],
        role=user_data["role"],
        status="active",
        is_active=True,
        hashed_password=password_hash,
    )
    db.add(user)
    return user


def main():
    db = SessionLocal()
    try:
        org = get_or_create_org(db)
        dept = get_or_create_department(db, org.id)
        users = [upsert_user(db, org.id, dept.id, item) for item in DEMO_USERS]
        db.commit()

        print("Demo accounts are ready.")
        print(f"Organization: {org.name}")
        print(f"Department: {dept.name}")
        for user in users:
            print(f"{user.role}: {user.email} / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
