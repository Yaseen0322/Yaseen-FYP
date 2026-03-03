"""
Integration Models - Phase 3
Slack, Jira, and other third-party integrations
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class IntegrationType(str, enum.Enum):
    SLACK = "slack"
    JIRA = "jira"
    MICROSOFT_TEAMS = "microsoft_teams"
    GOOGLE_WORKSPACE = "google_workspace"


class Integration(Base):
    """Third-party integrations configuration"""
    __tablename__ = "integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Integration type
    integration_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=False)
    is_configured = Column(Boolean, default=False)
    
    # Credentials (encrypted)
    config_json = Column(JSON, default={})
    # For Slack: {"webhook_url": "...", "bot_token": "..."}
    # For Jira: {"api_url": "...", "api_token": "...", "project_key": "..."}
    
    # Last sync info
    last_sync_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")


class SSOProvider(Base):
    """SSO Provider Configuration"""
    __tablename__ = "sso_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Provider type: google, microsoft, okta, saml
    provider_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    
    # Configuration
    config_json = Column(JSON, default={})
    # For Google: {"client_id": "...", "client_secret": "...", "domain": "..."}
    # For Microsoft: {"client_id": "...", "client_secret": "...", "tenant_id": "..."}
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization")


class MLClassification(Base):
    """ML Classification Results"""
    __tablename__ = "ml_classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Classification type
    classification_type = Column(String(50), nullable=False)  # domain, app
    input_value = Column(String(255), nullable=False)  # domain or app name
    
    # Classification result
    predicted_category = Column(String(100))
    predicted_label = Column(String(50))  # productive, unproductive, neutral
    confidence = Column(Integer)  # 0-100
    
    # Status
    is_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
