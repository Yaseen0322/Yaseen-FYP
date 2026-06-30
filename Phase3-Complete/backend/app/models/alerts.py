"""
Alert Models - Phase 2
Tracks alerts for excessive idle, camera off, low productivity
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class AlertType(str, enum.Enum):
    EXCESSIVE_IDLE = "excessive_idle"
    CAMERA_OFF_LONG = "camera_off_long"
    LOW_PRODUCTIVITY = "low_productivity"
    ABSENT_DURING_HOURS = "absent_during_hours"
    UNUSUAL_ACTIVITY = "unusual_activity"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertRule(Base):
    """Organization-level alert rules"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Rule configuration
    name = Column(String(255), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default=AlertSeverity.MEDIUM.value)
    is_active = Column(Boolean, default=True)
    
    # Threshold settings (JSON for flexibility)
    config_json = Column(JSON, default={})
    # e.g., {"threshold_minutes": 60, "check_interval": 30}
    
    # Notification settings
    notify_employee = Column(Boolean, default=False)
    notify_manager = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Alert(Base):
    """Individual alert instances"""
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_org_triggered", "org_id", "triggered_at"),
        Index("ix_alerts_user_read_triggered", "user_id", "is_read", "triggered_at"),
        Index("ux_alerts_dedupe_key", "dedupe_key", unique=True),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default=AlertSeverity.MEDIUM.value)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    
    # Context data
    context_json = Column(JSON, default={})
    # e.g., {"idle_duration_sec": 7200, "date": "2024-01-15"}
    dedupe_key = Column(String(255), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True))
    
    # Timestamps
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])


class DepartmentSummary(Base):
    """Pre-computed department-level summaries"""
    __tablename__ = "department_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    dept_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    
    # Aggregated metrics
    employee_count = Column(Integer, default=0)
    total_focus_sec = Column(Integer, default=0)
    total_idle_sec = Column(Integer, default=0)
    total_present_sec = Column(Integer, default=0)
    total_productive_sec = Column(Integer, default=0)
    total_unproductive_sec = Column(Integer, default=0)
    
    # Averages
    avg_focus_sec = Column(Integer, default=0)
    avg_present_sec = Column(Integer, default=0)
    avg_productivity_percent = Column(Integer, default=0)
    
    # Top items
    top_apps_json = Column(JSON, default=[])
    top_domains_json = Column(JSON, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    department = relationship("Department")
