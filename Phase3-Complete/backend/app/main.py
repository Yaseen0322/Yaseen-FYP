"""
Privacy-Preserving Employee Activity Tracker - Backend API
Main FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import verify_schema_up_to_date
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    verify_schema_up_to_date()
    print("Database schema verified")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Privacy-Preserving Employee Activity Tracker API
    
    This API provides:
    - Employee authentication and management
    - Activity data ingestion (app usage, idle time, presence, browser usage)
    - Employee personal dashboard data
    - Manager dashboard with team analytics
    
    Privacy-First Design:
    - No screenshots
    - No webcam images/videos stored
    - No keystroke content logging
    - Only timestamps and app/domain names stored
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
default_dev_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "app://.",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or (
        default_dev_origins if settings.ENVIRONMENT in {"development", "test"} else []
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    Root endpoint - API info
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
