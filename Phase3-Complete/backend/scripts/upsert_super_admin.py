"""
Create or update the local super admin account.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User


SUPER_ADMIN_EMAIL = "admin@yaseenfyp.com"
SUPER_ADMIN_PASSWORD = "Password123!"


def get_or_create_org(db):
    org = db.query(Organization).order_by(Organization.id.asc()).first()
    if org:
        return org

    org = Organization(
        name="Yaseen FYP Organization",
        timezone="Asia/Karachi",
        retention_days=90,
        is_active=True,
    )
    db.add(org)
    db.flush()
    return org


def main():
    db = SessionLocal()
    try:
        org = get_or_create_org(db)
        user = db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first()
        password_hash = get_password_hash(SUPER_ADMIN_PASSWORD)

        if user:
            user.org_id = org.id
            user.name = "Super Admin"
            user.role = "super_admin"
            user.status = "active"
            user.is_active = True
            user.hashed_password = password_hash
        else:
            user = User(
                org_id=org.id,
                email=SUPER_ADMIN_EMAIL,
                name="Super Admin",
                employee_id="ADMIN-001",
                role="super_admin",
                status="active",
                is_active=True,
                hashed_password=password_hash,
            )
            db.add(user)

        db.commit()
        print("Super admin account is ready.")
        print(f"Email: {SUPER_ADMIN_EMAIL}")
        print(f"Password: {SUPER_ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
