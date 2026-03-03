# API module
from fastapi import APIRouter
from .auth import router as auth_router
from .users import router as users_router
from .organizations import router as org_router
from .devices import router as devices_router
from .ingest import router as ingest_router
from .reports import router as reports_router
from .manager import router as manager_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(org_router, prefix="/org", tags=["Organization"])
api_router.include_router(devices_router, prefix="/devices", tags=["Devices"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["Data Ingestion"])
api_router.include_router(reports_router, prefix="/me", tags=["Employee Reports"])
api_router.include_router(manager_router, prefix="/manager", tags=["Manager Dashboard"])
