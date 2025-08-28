"""User and API key models."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication and action ownership."""

    __tablename__ = "users"

    # Basic user info
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Usage tracking
    total_actions_run = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Preferences
    default_region = Column(String(10), default="lax", nullable=False)
    enable_screenshots = Column(Boolean, default=True, nullable=False)
    enable_webhooks = Column(Boolean, default=True, nullable=False)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    stored_actions = relationship("StoredAction", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', email='{self.email}')>"


class APIKey(Base, UUIDMixin, TimestampMixin):
    """API keys for external service integration."""

    __tablename__ = "api_keys"

    # Key information
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, doc="Human-readable name for the key")
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    key_prefix = Column(String(20), nullable=False, doc="First few characters for identification")

    # Status and usage
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Permissions and limits
    rate_limit_per_hour = Column(Integer, default=500, nullable=False)
    allowed_actions = Column(Text, nullable=True, doc="JSON array of allowed action types")
    allowed_domains = Column(Text, nullable=True, doc="JSON array of allowed domains")

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid and usable."""
        return self.is_active and not self.is_expired

    def __repr__(self) -> str:
        return f"<APIKey(id='{self.id}', name='{self.name}', prefix='{self.key_prefix}')>"
