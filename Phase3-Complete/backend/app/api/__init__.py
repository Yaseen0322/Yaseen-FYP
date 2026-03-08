# API module
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .organizations import router as org_router
from .devices import router as devices_router
from .ingest import router as ingest_router
from .reports import router as reports_router
from .manager import router as manager_router
from .alerts import router as alerts_router
from .department_analytics import router as analytics_router
from .integrations import router as integrations_router
from .sso_auth import router as sso_router
from .ml import router as ml_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(org_router, prefix="/org", tags=["Organization"])
api_router.include_router(devices_router, prefix="/devices", tags=["Devices"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["Data Ingestion"])
api_router.include_router(reports_router, prefix="/me", tags=["Employee Reports"])
api_router.include_router(manager_router, prefix="/manager", tags=["Manager Dashboard"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Department Analytics"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(sso_router, prefix="/sso", tags=["SSO"])
api_router.include_router(ml_router, prefix="/ml", tags=["ML Classification"])
