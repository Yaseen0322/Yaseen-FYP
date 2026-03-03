"""
Daily Summary Model - Pre-computed daily aggregates
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Date (in org timezone)
    date = Column(Date, nullable=False, index=True)
    
    # Time summaries (in seconds)
    focus_sec = Column(Integer, default=0)  # Active app usage time
    idle_sec = Column(Integer, default=0)   # Idle time
    present_sec = Column(Integer, default=0)  # Webcam present
    absent_sec = Column(Integer, default=0)   # Webcam absent
    camera_off_sec = Column(Integer, default=0)  # Camera unavailable
    
    # Productivity breakdown
    productive_sec = Column(Integer, default=0)
    unproductive_sec = Column(Integer, default=0)
    neutral_sec = Column(Integer, default=0)
    
    # Top items (JSON arrays)
    top_apps_json = Column(JSON, default=[])
    top_domains_json = Column(JSON, default=[])
    
    # Session info
    first_activity = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="daily_summaries")
