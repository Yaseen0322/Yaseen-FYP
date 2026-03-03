"""
Presence Model - Webcam-based presence detection intervals
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class PresenceState(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    CAMERA_OFF = "camera_off"


class PresenceInterval(Base):
    __tablename__ = "presence_intervals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    
    # State: present, absent, camera_off
    state = Column(String(50), nullable=False, index=True)
    
    # Time tracking
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="presence_intervals")
    device = relationship("Device", back_populates="presence_intervals")
