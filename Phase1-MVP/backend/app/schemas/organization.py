"""
Organization and Department Schemas
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrganizationBase(BaseModel):
    name: str
    timezone: str = "Asia/Karachi"
    retention_days: int = 90


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentResponse(DepartmentBase):
    id: int
    org_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
