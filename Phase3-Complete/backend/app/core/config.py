"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from typing import Optional, List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Employee Activity Tracker"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = Field(default_factory=list)
    
    # Database - defaults to SQLite for testing, use PostgreSQL in production
    DATABASE_URL: str = "sqlite:///activity_tracker.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Settings
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OAUTH_STATE_EXPIRE_MINUTES: int = 10
    
    # Organization Defaults
    DEFAULT_TIMEZONE: str = "Asia/Karachi"
    DEFAULT_IDLE_THRESHOLD_SECONDS: int = 120
    DEFAULT_RETENTION_DAYS: int = 90
    
    # Webcam Service
    WEBCAM_SERVICE_URL: str = "http://localhost:8001"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return value

    @model_validator(mode="after")
    def validate_security_defaults(self):
        environment = (self.ENVIRONMENT or "development").lower()
        object.__setattr__(self, "ENVIRONMENT", environment)

        secret_key = self.SECRET_KEY
        if not secret_key:
            if environment == "production":
                raise ValueError("SECRET_KEY must be configured in production")
            secret_key = "dev-insecure-secret-key-change-before-release"
            object.__setattr__(self, "SECRET_KEY", secret_key)

        if environment == "production":
            if secret_key == "dev-insecure-secret-key-change-before-release" or len(secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("SQLite is not allowed in production")

        return self


settings = Settings()
