"""
Organization and Department API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin, get_current_manager
from app.models.user import User
from app.models.organization import Organization, Department
from app.schemas.organization import (
    OrganizationResponse, OrganizationCreate,
    DepartmentResponse, DepartmentCreate
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
    dept = Department(
        org_id=current_user.org_id,
        name=dept_data.name,
        description=dept_data.description
    )
    db.add(dept)
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
    
    db.delete(dept)
    db.commit()
    
    return {"message": "Department deleted"}
