"""
Browser Usage Model and Domain Rules
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProductivityLabel(str, enum.Enum):
    PRODUCTIVE = "productive"
    UNPRODUCTIVE = "unproductive"
    NEUTRAL = "neutral"


class BrowserUsage(Base):
    __tablename__ = "browser_usage"
    __table_args__ = (
        Index("ix_browser_usage_user_time", "user_id", "start_ts", "end_ts"),
        Index("ix_browser_usage_user_label_time", "user_id", "label", "start_ts"),
        Index("ix_browser_usage_device_time", "device_id", "start_ts", "end_ts"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    
    # Browser info
    browser = Column(String(100), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    
    # Time tracking
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    
    # Classification
    category = Column(String(100))  # e.g., "Social Media", "Development", "Learning"
    label = Column(String(50))  # productive, unproductive, neutral
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="browser_usages")
    device = relationship("Device", back_populates="browser_usages")


class DomainRule(Base):
    __tablename__ = "domain_rules"
    __table_args__ = (
        Index("ix_domain_rules_org_domain", "org_id", "domain"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Domain matching
    domain = Column(String(255), nullable=False, index=True)  # e.g., "youtube.com", "*.github.com"
    
    # Classification
    category = Column(String(100), nullable=False)
    label = Column(String(50), nullable=False)  # productive, unproductive, neutral
    
    # Department overrides (JSON: {dept_id: "productive"})
    dept_overrides_json = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="domain_rules")
