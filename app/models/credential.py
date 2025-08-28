"""Credential models for secure storage and management."""

import json
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class CredentialType(str, Enum):
    """Types of credentials that can be stored."""

    USERNAME_PASSWORD = "username_password"
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    BEARER_TOKEN = "bearer_token"
    COOKIE_SESSION = "cookie_session"
    CUSTOM = "custom"


class Credential(Base, UUIDMixin, TimestampMixin):
    """Secure credential storage with domain-based organization."""

    __tablename__ = "credentials"

    # Ownership
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Credential identification
    name = Column(String(255), nullable=False, doc="User-friendly name for the credential")
    domain = Column(String(255), nullable=False, index=True, doc="Domain this credential is for")
    credential_type = Column(String(50), nullable=False, doc="Type of credential")

    # Encrypted credential data
    encrypted_data = Column(Text, nullable=False, doc="Fernet-encrypted credential data")

    # Metadata
    description = Column(Text, nullable=True, doc="Optional description")
    tags = Column(Text, nullable=True, doc="JSON array of tags for organization")

    # Status and validation
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime, nullable=True)
    last_validated = Column(DateTime, nullable=True)
    validation_status = Column(String(20), nullable=True, doc="last_known_status: valid, invalid, unknown")
    usage_count = Column(Integer, default=0, nullable=False)

    # Security
    access_restricted_to_actions = Column(Text, nullable=True, doc="JSON array of action IDs that can use this credential")
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="credentials")

    @property
    def is_expired(self) -> bool:
        """Check if the credential has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if credential is active and not expired."""
        return self.is_active and not self.is_expired

    @property
    def tags_list(self) -> list[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    @tags_list.setter
    def tags_list(self, value: list[str]) -> None:
        """Set tags from a list."""
        self.tags = json.dumps(value) if value else None

    @property
    def allowed_actions(self) -> list[str] | None:
        """Get allowed actions as a list."""
        if not self.access_restricted_to_actions:
            return None
        try:
            return json.loads(self.access_restricted_to_actions)
        except (json.JSONDecodeError, TypeError):
            return None

    @allowed_actions.setter
    def allowed_actions(self, value: list[str] | None) -> None:
        """Set allowed actions from a list."""
        self.access_restricted_to_actions = json.dumps(value) if value else None

    def can_be_used_by_action(self, action_id: str) -> bool:
        """Check if this credential can be used by a specific action."""
        allowed = self.allowed_actions
        if allowed is None:
            return True  # No restrictions
        return action_id in allowed

    def __repr__(self) -> str:
        return f"<Credential(id='{self.id}', name='{self.name}', domain='{self.domain}', type='{self.credential_type}')>"
