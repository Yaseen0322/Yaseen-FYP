"""
User Schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    name: str
    employee_id: Optional[str] = None
    dept_id: Optional[int] = None


class UserCreate(UserBase):
    password: str
    role: str = "employee"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    dept_id: Optional[int] = None
    role: Optional[str] = None
    status: Optional[str] = None


class UserResponse(UserBase):
    id: int
    org_id: int
    role: str
    status: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
