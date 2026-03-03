"""
Device Model - Registered employee machines
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Device identification
    machine_id = Column(String(255), unique=True, index=True, nullable=False)
    hostname = Column(String(255))
    os = Column(String(100))
    os_version = Column(String(100))
    
    # App info
    app_version = Column(String(50))
    
    # Status
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="devices")
    app_usages = relationship("AppUsage", back_populates="device")
    idle_intervals = relationship("IdleInterval", back_populates="device")
    presence_intervals = relationship("PresenceInterval", back_populates="device")
    browser_usages = relationship("BrowserUsage", back_populates="device")
