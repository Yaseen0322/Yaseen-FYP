"""
User Model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    
    # Basic info
    email = Column(String(255), unique=True, index=True, nullable=False)
    employee_id = Column(String(100), index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Role and status
    role = Column(String(50), default=UserRole.EMPLOYEE.value)
    status = Column(String(50), default=UserStatus.ACTIVE.value)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    devices = relationship("Device", back_populates="user")
    app_usages = relationship("AppUsage", back_populates="user")
    idle_intervals = relationship("IdleInterval", back_populates="user")
    presence_intervals = relationship("PresenceInterval", back_populates="user")
    browser_usages = relationship("BrowserUsage", back_populates="user")
    daily_summaries = relationship("DailySummary", back_populates="user")
