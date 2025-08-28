"""Application configuration using pydantic-settings."""

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application Info
    app_name: str = Field(default="Steel.run", env="APP_NAME")
    version: str = "1.0.0"
    description: str = "Atomic Web Functions Platform"
    debug: bool = Field(default=False, env="DEBUG")
    env: str = Field(default="development", env="ENV")

    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=False, env="RELOAD")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    credential_encryption_key: str = Field(..., env="CREDENTIAL_ENCRYPTION_KEY")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./steel_actions.db", env="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Steel Configuration
    steel_api_key: str = Field(..., env="STEEL_API_KEY")
    default_region: str = Field(default="lax", env="DEFAULT_REGION")
    max_concurrent_sessions: int = Field(default=10, env="MAX_CONCURRENT_SESSIONS")
    default_session_timeout: int = Field(default=30000, env="DEFAULT_SESSION_TIMEOUT")
    enable_captcha_solving: bool = Field(default=True, env="ENABLE_CAPTCHA_SOLVING")

    # Anthropic Configuration
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")

    # Rate Limiting
    rate_limit_per_ip: int = Field(default=100, env="RATE_LIMIT_PER_IP")
    rate_limit_per_user: int = Field(default=500, env="RATE_LIMIT_PER_USER")
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")

    # External Services
    enable_webhooks: bool = Field(default=True, env="ENABLE_WEBHOOKS")
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")

    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    log_level: str = Field(default="info", env="LOG_LEVEL")

    # CORS Settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Blocked domains for security
    blocked_domains: list[str] = Field(
        default=[
            "maliciousbook.com",
            "evilvideos.com",
            "darkwebforum.com",
            "shadytok.com",
            "suspiciouspins.com",
        ]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from environment string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("blocked_domains", mode="before")
    @classmethod
    def assemble_blocked_domains(cls, v):
        """Parse blocked domains from environment string."""
        if isinstance(v, str):
            return [domain.strip() for domain in v.split(",")]
        return v

    def validate_required_keys(self) -> bool:
        """Validate that all required API keys are present."""
        required_keys = [
            self.steel_api_key,
            self.anthropic_api_key,
            self.secret_key,
            self.credential_encryption_key,
        ]

        missing_keys = [key for key in required_keys if not key]

        if missing_keys:
            missing_names = []
            if not self.steel_api_key:
                missing_names.append("STEEL_API_KEY")
            if not self.anthropic_api_key:
                missing_names.append("ANTHROPIC_API_KEY")
            if not self.secret_key:
                missing_names.append("SECRET_KEY")
            if not self.credential_encryption_key:
                missing_names.append("CREDENTIAL_ENCRYPTION_KEY")

            raise ValueError(f"Missing required configuration: {', '.join(missing_names)}")

        return True

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.env.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env.lower() == "production"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in environment


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


# Validate configuration on import
if os.getenv("SKIP_CONFIG_VALIDATION") != "true":
    settings.validate_required_keys()
