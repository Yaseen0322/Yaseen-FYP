"""
Organization and Department API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin, get_current_manager
from app.models.user import User
from app.models.organization import Organization, Department
from app.schemas.organization import (
    OrganizationResponse, OrganizationCreate,
    DepartmentResponse, DepartmentCreate, DepartmentUpdate
)

router = APIRouter()


@router.get("/", response_model=OrganizationResponse)
async def get_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's organization
    """
    org = db.query(Organization).filter(
        Organization.id == current_user.org_id
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return OrganizationResponse.model_validate(org)


@router.patch("/", response_model=OrganizationResponse)
async def update_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Update organization settings (Admin only)
    """
    org = db.query(Organization).filter(
        Organization.id == current_user.org_id
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    for field, value in org_data.model_dump().items():
        setattr(org, field, value)
    
    db.commit()
    db.refresh(org)
    
    return OrganizationResponse.model_validate(org)


# Department endpoints
@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all departments in organization
    """
    departments = db.query(Department).filter(
        Department.org_id == current_user.org_id
    ).all()
    
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    dept_data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Create new department (Manager only)
    """
    existing = db.query(Department).filter(
        Department.org_id == current_user.org_id,
        func.lower(Department.name) == dept_data.name.strip().lower(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department name already exists")

    dept = Department(
        org_id=current_user.org_id,
        name=dept_data.name.strip(),
        description=dept_data.description
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    
    return DepartmentResponse.model_validate(dept)


@router.patch("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: int,
    dept_data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Update department details (Manager only)
    """
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.org_id == current_user.org_id
    ).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = dept_data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"]:
        normalized_name = update_data["name"].strip()
        existing = db.query(Department).filter(
            Department.org_id == current_user.org_id,
            func.lower(Department.name) == normalized_name.lower(),
            Department.id != dept.id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Department name already exists")
        update_data["name"] = normalized_name

    for field, value in update_data.items():
        setattr(dept, field, value)

    db.commit()
    db.refresh(dept)
    return DepartmentResponse.model_validate(dept)


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_manager)
):
    """
    Delete department (Manager only)
    """
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.org_id == current_user.org_id
    ).first()
    
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    assigned_users = db.query(func.count(User.id)).filter(
        User.org_id == current_user.org_id,
        User.dept_id == dept.id
    ).scalar() or 0
    if assigned_users:
        raise HTTPException(
            status_code=400,
            detail=f"Department has {assigned_users} assigned user(s). Reassign them before deleting the department."
        )
    
    db.delete(dept)
    db.commit()
    
    return {"message": "Department deleted"}
