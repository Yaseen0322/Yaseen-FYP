"""
Integrations API Routes - Phase 3
Slack, Jira, and SSO integrations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.integrations import Integration, SSOProvider, IntegrationType

router = APIRouter()


# Schemas
class IntegrationCreate(BaseModel):
    integration_type: str
    name: str
    config_json: Dict[str, Any] = {}


class IntegrationResponse(BaseModel):
    id: int
    org_id: int
    integration_type: str
    name: str
    is_active: bool
    is_configured: bool
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    
    class Config:
        from_attributes = True


class SSOProviderCreate(BaseModel):
    provider_type: str
    name: str
    config_json: Dict[str, Any] = {}


class SSOProviderResponse(BaseModel):
    id: int
    org_id: int
    provider_type: str
    name: str
    is_active: bool
    is_primary: bool
    
    class Config:
        from_attributes = True


# Integration CRUD
@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List all integrations for organization"""
    integrations = db.query(Integration).filter(
        Integration.org_id == current_user.org_id
    ).all()
    return integrations


@router.post("/", response_model=IntegrationResponse)
async def create_integration(
    data: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create new integration"""
    integration = Integration(
        org_id=current_user.org_id,
        integration_type=data.integration_type,
        name=data.name,
        config_json=data.config_json,
        is_configured=bool(data.config_json)
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


@router.patch("/{integration_id}")
async def update_integration(
    integration_id: int,
    config_json: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update integration configuration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.org_id == current_user.org_id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    integration.config_json = config_json
    integration.is_configured = True
    db.commit()
    
    return {"message": "Integration updated"}


@router.post("/{integration_id}/toggle")
async def toggle_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Enable/disable integration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.org_id == current_user.org_id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if not integration.is_configured:
        raise HTTPException(status_code=400, detail="Integration not configured")
    
    integration.is_active = not integration.is_active
    db.commit()
    
    return {"message": "Integration toggled", "is_active": integration.is_active}


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Test integration connection"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.org_id == current_user.org_id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    # Test based on type
    try:
        if integration.integration_type == IntegrationType.SLACK.value:
            success = await test_slack_connection(integration.config_json)
        elif integration.integration_type == IntegrationType.JIRA.value:
            success = await test_jira_connection(integration.config_json)
        else:
            success = False
        
        if success:
            integration.last_sync_at = datetime.utcnow()
            integration.last_error = None
        else:
            integration.last_error = "Connection test failed"
        
        db.commit()
        
        return {"success": success, "message": "Test completed"}
    except Exception as e:
        integration.last_error = str(e)
        db.commit()
        return {"success": False, "message": str(e)}


async def test_slack_connection(config: Dict) -> bool:
    """Test Slack webhook connection"""
    import httpx
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={"text": "Activity Tracker test message"}
            )
            return response.status_code == 200
    except:
        return False


async def test_jira_connection(config: Dict) -> bool:
    """Test Jira API connection"""
    import httpx
    api_url = config.get("api_url")
    api_token = config.get("api_token")
    email = config.get("email")
    
    if not all([api_url, api_token, email]):
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{api_url}/rest/api/3/myself",
                auth=(email, api_token)
            )
            return response.status_code == 200
    except:
        return False


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Delete integration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.org_id == current_user.org_id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    db.delete(integration)
    db.commit()
    
    return {"message": "Integration deleted"}


# SSO Provider CRUD
@router.get("/sso", response_model=List[SSOProviderResponse])
async def list_sso_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List SSO providers"""
    providers = db.query(SSOProvider).filter(
        SSOProvider.org_id == current_user.org_id
    ).all()
    return providers


@router.post("/sso", response_model=SSOProviderResponse)
async def create_sso_provider(
    data: SSOProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create SSO provider"""
    provider = SSOProvider(
        org_id=current_user.org_id,
        provider_type=data.provider_type,
        name=data.name,
        config_json=data.config_json
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.post("/sso/{provider_id}/toggle")
async def toggle_sso_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Enable/disable SSO provider"""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == current_user.org_id
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    provider.is_active = not provider.is_active
    db.commit()
    
    return {"message": "SSO provider toggled", "is_active": provider.is_active}
