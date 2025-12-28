"""
Configuration settings for MadanSara
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production"
    API_VERSION: str = "v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    # Database
    DATABASE_URL: str = "postgresql://postgres:madansara_password@localhost:5434/madansara"
    DATABASE_PUBLIC_URL: str = "postgresql://postgres:madansara_password@localhost:5434/madansara"

    # Redis
    REDIS_URL: str = "redis://localhost:6381/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9004"
    MINIO_ACCESS_KEY: str = "madansara-minio-key"
    MINIO_SECRET_KEY: str = "madansara-minio-secret"
    MINIO_SECURE: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6381/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6381/0"

    # En Garde Integration
    ENGARDE_API_URL: str = "http://localhost:8000"
    ENGARDE_API_KEY: str = ""
    ENGARDE_TENANT_UUID: str = ""

    # AI Services
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Email Services
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@engarde.com"
    SENDGRID_FROM_NAME: str = "En Garde"

    # Social Media APIs
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""

    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_ACCESS_TOKEN: str = ""

    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_TOKEN_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""

    # WhatsApp Business
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    # Google Analytics
    GOOGLE_ANALYTICS_PROPERTY_ID: str = ""
    GOOGLE_ANALYTICS_CREDENTIALS_JSON: str = ""

    # A/B Testing
    AB_TEST_MIN_SAMPLE_SIZE: int = 100
    AB_TEST_CONFIDENCE_LEVEL: float = 0.95

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Feature Flags
    ENABLE_EMAIL_OUTREACH: bool = True
    ENABLE_SOCIAL_DM: bool = True
    ENABLE_WEBSITE_TRACKING: bool = True
    ENABLE_AB_TESTING: bool = True

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
