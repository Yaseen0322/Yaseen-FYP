"""
Activity Models - App Usage and Idle Intervals
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class AppUsage(Base):
    __tablename__ = "app_usage"
    __table_args__ = (
        Index("ix_app_usage_user_time", "user_id", "start_ts", "end_ts"),
        Index("ix_app_usage_device_time", "device_id", "start_ts", "end_ts"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    
    # Application info
    app_name = Column(String(255), nullable=False, index=True)
    window_title = Column(String(500))  # Optional, can be masked
    
    # Time tracking
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="app_usages")
    device = relationship("Device", back_populates="app_usages")


class IdleInterval(Base):
    __tablename__ = "idle_intervals"
    __table_args__ = (
        Index("ix_idle_intervals_user_time", "user_id", "start_ts", "end_ts"),
        Index("ix_idle_intervals_device_time", "device_id", "start_ts", "end_ts"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    
    # Time tracking
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="idle_intervals")
    device = relationship("Device", back_populates="idle_intervals")
