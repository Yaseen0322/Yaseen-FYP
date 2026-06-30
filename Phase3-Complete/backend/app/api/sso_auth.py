"""
SSO Authentication Routes - Phase 3
Google and Microsoft OAuth2 authentication
"""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
import httpx
from app.core.crypto import decrypt_json_payload
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_oauth_state,
    create_refresh_token,
    decode_oauth_state,
    generate_pkce_challenge,
    generate_pkce_verifier,
    get_password_hash,
)
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


def validate_redirect_uri(config: dict, redirect_uri: str):
    allowed = config.get("allowed_redirect_uris") or []
    if not allowed and config.get("redirect_uri"):
        allowed = [config.get("redirect_uri")]

    if not allowed:
        raise HTTPException(status_code=400, detail="SSO redirect URI is not configured")

    if redirect_uri not in allowed:
        raise HTTPException(status_code=400, detail="Redirect URI is not allowed")


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
    
    config = decrypt_json_payload(provider.config_json)
    validate_redirect_uri(config, redirect_uri)
    client_id = config.get("client_id")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="Google client ID not configured")

    code_verifier = generate_pkce_verifier()
    state = create_oauth_state("google", org_id, redirect_uri, code_verifier)
    
    # Build auth URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": generate_pkce_challenge(code_verifier),
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "select_account"
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    state_payload = decode_oauth_state(state)
    if not state_payload or state_payload.get("provider") != "google":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    org_id = int(state_payload["org_id"])
    if redirect_uri != state_payload.get("redirect_uri"):
        raise HTTPException(status_code=400, detail="Redirect URI mismatch")
    
    # Get SSO provider config
    provider = db.query(SSOProvider).filter(
        SSOProvider.org_id == org_id,
        SSOProvider.provider_type == "google",
        SSOProvider.is_active == True
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Google SSO not configured")
    
    config = decrypt_json_payload(provider.config_json)
    validate_redirect_uri(config, redirect_uri)
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
                "code_verifier": state_payload.get("code_verifier"),
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

    if not email:
        raise HTTPException(status_code=400, detail="Google account email is required")
    
    # Validate domain if configured
    if allowed_domain:
        email_domain = email.split("@")[1]
        if email_domain != allowed_domain:
            raise HTTPException(status_code=403, detail=f"Email domain must be @{allowed_domain}")
    
    # Find or create user
    user = db.query(User).filter(
        User.email == email,
        User.org_id == org_id
    ).first()

    existing_in_other_org = db.query(User).filter(
        User.email == email,
        User.org_id != org_id
    ).first()
    if existing_in_other_org:
        raise HTTPException(status_code=403, detail="This email is already assigned to another organization")
    
    if not user:
        # Create new user
        user = User(
            org_id=org_id,
            email=email,
            name=name,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
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
    
    config = decrypt_json_payload(provider.config_json)
    validate_redirect_uri(config, redirect_uri)
    client_id = config.get("client_id")
    tenant_id = config.get("tenant_id", "common")
    
    if not client_id:
        raise HTTPException(status_code=400, detail="Microsoft client ID not configured")
    
    auth_url = MICROSOFT_AUTH_URL.format(tenant=tenant_id)
    code_verifier = generate_pkce_verifier()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile User.Read",
        "state": create_oauth_state("microsoft", org_id, redirect_uri, code_verifier),
        "code_challenge": generate_pkce_challenge(code_verifier),
        "code_challenge_method": "S256",
        "response_mode": "query"
    }
    
    return {"auth_url": f"{auth_url}?{urlencode(params)}"}


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str,
    redirect_uri: str,
    db: Session = Depends(get_db)
):
    """Handle Microsoft OAuth callback"""
    state_payload = decode_oauth_state(state)
    if not state_payload or state_payload.get("provider") != "microsoft":
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    org_id = int(state_payload["org_id"])
    if redirect_uri != state_payload.get("redirect_uri"):
        raise HTTPException(status_code=400, detail="Redirect URI mismatch")
    
    provider = db.query(SSOProvider).filter(
        SSOProvider.org_id == org_id,
        SSOProvider.provider_type == "microsoft",
        SSOProvider.is_active == True
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Microsoft SSO not configured")
    
    config = decrypt_json_payload(provider.config_json)
    validate_redirect_uri(config, redirect_uri)
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    tenant_id = config.get("tenant_id", "common")
    allowed_domain = config.get("domain")
    
    token_url = MICROSOFT_TOKEN_URL.format(tenant=tenant_id)
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code_verifier": state_payload.get("code_verifier"),
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

    if not email:
        raise HTTPException(status_code=400, detail="Microsoft account email is required")

    if allowed_domain:
        email_domain = email.split("@")[1]
        if email_domain != allowed_domain:
            raise HTTPException(status_code=403, detail=f"Email domain must be @{allowed_domain}")
    
    user = db.query(User).filter(
        User.email == email,
        User.org_id == org_id
    ).first()

    existing_in_other_org = db.query(User).filter(
        User.email == email,
        User.org_id != org_id
    ).first()
    if existing_in_other_org:
        raise HTTPException(status_code=403, detail="This email is already assigned to another organization")
    
    if not user:
        user = User(
            org_id=org_id,
            email=email,
            name=name,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
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
