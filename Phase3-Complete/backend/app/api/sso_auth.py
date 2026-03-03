"""
SSO Authentication Routes - Phase 3
Google and Microsoft OAuth2 authentication
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import httpx
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from app.models.user import User
from app.models.integrations import SSOProvider

router = APIRouter()


# Google OAuth2
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Microsoft OAuth2
MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"


@router.get("/google/login")
async def google_login(
    org_id: int,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    """Initiate Google OAuth login"""
    # Get SSO provider config
    provider = db.query(SSOProvider).filter(
        SSOProvider.org_id == org_id,
        SSOProvider.provider_type == "google",
        SSOProvider.is_active == True
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Google SSO not configured")
    
    config = provider.config_json
    client_id = config.get("client_id")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="Google client ID not configured")
    
    # Build auth URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": f"{org_id}",
        "access_type": "offline",
        "prompt": "select_account"
    }
    
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{GOOGLE_AUTH_URL}?{query}"
    
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    org_id = int(state)
    
    # Get SSO provider config
    provider = db.query(SSOProvider).filter(
        SSOProvider.org_id == org_id,
        SSOProvider.provider_type == "google",
        SSOProvider.is_active == True
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Google SSO not configured")
    
    config = provider.config_json
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    allowed_domain = config.get("domain")
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # Get user info
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        userinfo = userinfo_response.json()
    
    email = userinfo.get("email")
    name = userinfo.get("name")
    
    # Validate domain if configured
    if allowed_domain:
        email_domain = email.split("@")[1]
        if email_domain != allowed_domain:
            raise HTTPException(status_code=403, detail=f"Email domain must be @{allowed_domain}")
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user
        user = User(
            org_id=org_id,
            email=email,
            name=name,
            hashed_password="",  # SSO users don't have password
            role="employee",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate tokens
    app_access_token = create_access_token(data={"sub": str(user.id)})
    app_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": app_access_token,
        "refresh_token": app_refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }


@router.get("/microsoft/login")
async def microsoft_login(
    org_id: int,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    """Initiate Microsoft OAuth login"""
    provider = db.query(SSOProvider).filter(
        SSOProvider.org_id == org_id,
        SSOProvider.provider_type == "microsoft",
        SSOProvider.is_active == True
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Microsoft SSO not configured")
    
    config = provider.config_json
    client_id = config.get("client_id")
    tenant_id = config.get("tenant_id", "common")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="Microsoft client ID not configured")
    
    auth_url = MICROSOFT_AUTH_URL.format(tenant=tenant_id)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile User.Read",
        "state": f"{org_id}",
        "response_mode": "query"
    }
    
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    
    return {"auth_url": f"{auth_url}?{query}"}


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    """Handle Microsoft OAuth callback"""
    org_id = int(state)
    
    provider = db.query(SSOProvider).filter(
        SSOProvider.org_id == org_id,
        SSOProvider.provider_type == "microsoft",
        SSOProvider.is_active == True
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Microsoft SSO not configured")
    
    config = provider.config_json
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    tenant_id = config.get("tenant_id", "common")
    
    token_url = MICROSOFT_TOKEN_URL.format(tenant=tenant_id)
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code")
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        userinfo_response = await client.get(
            MICROSOFT_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        userinfo = userinfo_response.json()
    
    email = userinfo.get("mail") or userinfo.get("userPrincipalName")
    name = userinfo.get("displayName")
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        user = User(
            org_id=org_id,
            email=email,
            name=name,
            hashed_password="",
            role="employee",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    app_access_token = create_access_token(data={"sub": str(user.id)})
    app_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": app_access_token,
        "refresh_token": app_refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }
