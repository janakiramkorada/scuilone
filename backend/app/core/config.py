import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")
    
    PROJECT_NAME: str = "SCuilONE - Multi-Industry Multi-Tenant CRM"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "scuilone-insecure-development-secret-key-change-in-prod-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OTP_EXPIRE_MINUTES: int = 10
    
    # Database (defaults to SQLite for frictionless local testing, PostgreSQL ready)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./scuilone.db"
    )
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # Email / SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@scuilone.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "SCuilONE Support")
    ENABLE_REAL_EMAIL: bool = os.getenv("ENABLE_REAL_EMAIL", "false").lower() == "true"


settings = Settings()

