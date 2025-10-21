"""Configuration settings for PARA Autopilot backend."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str

    # Anthropic API
    ANTHROPIC_API_KEY: str

    # Google OAuth (for MCP integrations)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # JWT & Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Environment
    ENVIRONMENT: str = "development"

    # Frontend URL (for CORS)
    FRONTEND_URL: str = "http://localhost:3000"

    # Claude Model Configuration
    CLAUDE_MODEL: str = "claude-haiku-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4000
    CLAUDE_TEMPERATURE: float = 0.5

    # Cost tracking (per million tokens)
    CLAUDE_HAIKU_INPUT_COST: float = 1.0
    CLAUDE_HAIKU_OUTPUT_COST: float = 5.0

    # Redis Configuration (Phase 6)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_MAX_CONNECTIONS: int = 10

    # Email Configuration (Phase 7)
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@para-autopilot.com"

    # Application URL (for email links)
    APP_URL: str = "http://localhost:3000"

    # Sentry Configuration (Phase 8)
    SENTRY_DSN: Optional[str] = None
    VERSION: str = "0.1.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
