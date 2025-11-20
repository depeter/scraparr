"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Scraparr"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://scraparr:scraparr@postgres:5432/scraparr"
    DATABASE_ECHO: bool = False

    # Security
    SECRET_KEY: str = "scraparr-super-secret-key-change-in-production-use-env-variable"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days for convenience

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    # Scraper settings
    MAX_CONCURRENT_SCRAPERS: int = 5
    SCRAPER_TIMEOUT: int = 300  # 5 minutes
    DEFAULT_USER_AGENT: str = "Scraparr/1.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
