"""
Integrations API Routes - Phase 3
Slack, Jira, and SSO integrations
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, field_validator, model_validator
from app.core.database import get_db
from app.core.crypto import decrypt_json_payload, encrypt_json_payload
from app.core.pagination import build_paginated_response
from app.core.security import get_current_admin
from app.models.user import User
from app.models.integrations import Integration, SSOProvider, IntegrationType

router = APIRouter()

SUPPORTED_INTEGRATIONS = {
    IntegrationType.SLACK.value,
    IntegrationType.JIRA.value,
}
SUPPORTED_SSO_PROVIDERS = {"google", "microsoft", "okta"}


# Schemas
class IntegrationCreate(BaseModel):
    integration_type: str
    name: str
    config_json: Dict[str, Any] = {}

    @field_validator("integration_type")
    @classmethod
    def validate_integration_type(cls, value: str):
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_INTEGRATIONS:
            raise ValueError("Unsupported integration type")
        return normalized

    @model_validator(mode="after")
    def validate_config(self):
        validate_integration_config(self.integration_type, self.config_json)
        return self


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None


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


class IntegrationDetailResponse(IntegrationResponse):
    config_json: Dict[str, Any]


class SSOProviderCreate(BaseModel):
    provider_type: str
    name: str
    config_json: Dict[str, Any] = {}

    @field_validator("provider_type")
    @classmethod
    def validate_provider_type(cls, value: str):
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_SSO_PROVIDERS:
            raise ValueError("Unsupported SSO provider")
        return normalized

    @model_validator(mode="after")
    def validate_config(self):
        validate_sso_config(self.provider_type, self.config_json)
        return self


class SSOProviderUpdate(BaseModel):
    name: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None


class SSOProviderResponse(BaseModel):
    id: int
    org_id: int
    provider_type: str
    name: str
    is_active: bool
    is_primary: bool
    
    class Config:
        from_attributes = True


class SSOProviderDetailResponse(SSOProviderResponse):
    config_json: Dict[str, Any]


def _ensure_required_fields(config_json: Dict[str, Any], required_fields: List[str], message: str):
    missing = [field for field in required_fields if not config_json.get(field)]
    if missing:
        raise ValueError(f"{message}: missing {', '.join(missing)}")


def validate_integration_config(integration_type: str, config_json: Dict[str, Any]):
    if integration_type == IntegrationType.SLACK.value:
        _ensure_required_fields(config_json, ["webhook_url"], "Slack configuration is incomplete")
    elif integration_type == IntegrationType.JIRA.value:
        _ensure_required_fields(config_json, ["api_url", "email", "api_token"], "Jira configuration is incomplete")
    else:
        raise ValueError("Unsupported integration type")


def validate_sso_config(provider_type: str, config_json: Dict[str, Any]):
    required = ["client_id", "client_secret", "redirect_uri"]
    if provider_type == "microsoft":
        required.append("tenant_id")
    _ensure_required_fields(config_json, required, "SSO configuration is incomplete")


def assert_valid_integration_config(integration_type: str, config_json: Dict[str, Any]):
    try:
        validate_integration_config(integration_type, config_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def assert_valid_sso_config(provider_type: str, config_json: Dict[str, Any]):
    try:
        validate_sso_config(provider_type, config_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Integration CRUD
@router.get("/")
async def list_integrations(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List all integrations for organization"""
    query = db.query(Integration).filter(
        Integration.org_id == current_user.org_id
    )
    total = query.count()
    integrations = query.order_by(Integration.created_at.desc(), Integration.id.desc()).offset(offset).limit(limit).all()
    return build_paginated_response(
        [IntegrationResponse.model_validate(item).model_dump() for item in integrations],
        total=total,
        limit=limit,
        offset=offset,
    )


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
        config_json=encrypt_json_payload(data.config_json),
        is_configured=bool(data.config_json)
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


@router.patch("/{integration_id}")
async def update_integration(
    integration_id: int,
    payload: IntegrationUpdate,
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

    if payload.name is not None:
        integration.name = payload.name

    if payload.config_json is not None:
        assert_valid_integration_config(integration.integration_type, payload.config_json)
        integration.config_json = encrypt_json_payload(payload.config_json)
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

    if integration.integration_type not in SUPPORTED_INTEGRATIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Integration type is not operationally supported")
    
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
        config = decrypt_json_payload(integration.config_json)
        if integration.integration_type == IntegrationType.SLACK.value:
            success = await test_slack_connection(config)
        elif integration.integration_type == IntegrationType.JIRA.value:
            success = await test_jira_connection(config)
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
@router.get("/sso")
async def list_sso_providers(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List SSO providers"""
    query = db.query(SSOProvider).filter(
        SSOProvider.org_id == current_user.org_id
    )
    total = query.count()
    providers = query.order_by(SSOProvider.created_at.desc(), SSOProvider.id.desc()).offset(offset).limit(limit).all()
    return build_paginated_response(
        [SSOProviderResponse.model_validate(item).model_dump() for item in providers],
        total=total,
        limit=limit,
        offset=offset,
    )


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
        config_json=encrypt_json_payload(data.config_json)
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.get("/sso/{provider_id}", response_model=SSOProviderDetailResponse)
async def get_sso_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == current_user.org_id,
    ).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return SSOProviderDetailResponse(
        **SSOProviderResponse.model_validate(provider).model_dump(),
        config_json=decrypt_json_payload(provider.config_json),
    )


@router.patch("/sso/{provider_id}")
async def update_sso_provider(
    provider_id: int,
    payload: SSOProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Update SSO provider configuration"""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == current_user.org_id,
    ).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if payload.name is not None:
        provider.name = payload.name

    if payload.config_json is not None:
        assert_valid_sso_config(provider.provider_type, payload.config_json)
        provider.config_json = encrypt_json_payload(payload.config_json)

    db.commit()
    return {"message": "SSO provider updated"}


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


@router.delete("/sso/{provider_id}")
async def delete_sso_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Delete an SSO provider"""
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.org_id == current_user.org_id,
    ).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    db.delete(provider)
    db.commit()
    return {"message": "SSO provider deleted"}


@router.get("/{integration_id}", response_model=IntegrationDetailResponse)
async def get_integration(
    integration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.org_id == current_user.org_id,
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return IntegrationDetailResponse(
        **IntegrationResponse.model_validate(integration).model_dump(),
        config_json=decrypt_json_payload(integration.config_json),
    )
