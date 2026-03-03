"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Employee Activity Tracker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database - defaults to SQLite for testing, use PostgreSQL in production
    DATABASE_URL: str = "sqlite:///./activity_tracker.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Settings
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Organization Defaults
    DEFAULT_TIMEZONE: str = "Asia/Karachi"
    DEFAULT_IDLE_THRESHOLD_SECONDS: int = 120
    DEFAULT_RETENTION_DAYS: int = 90
    
    # Webcam Service
    WEBCAM_SERVICE_URL: str = "http://localhost:8001"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
