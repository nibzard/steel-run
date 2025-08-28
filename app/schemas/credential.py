"""Credential schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..models.credential import CredentialType


class CredentialBase(BaseModel):
    """Base credential schema."""

    name: str = Field(..., min_length=1, max_length=255, description="User-friendly name")
    domain: str = Field(..., min_length=1, max_length=255, description="Domain this credential is for")
    credential_type: CredentialType = Field(..., description="Type of credential")
    description: str | None = Field(None, description="Optional description")
    tags: list[str] | None = Field(default_factory=list, description="Tags for organization")
    expires_at: datetime | None = Field(None, description="When credential expires")
    access_restricted_to_actions: list[str] | None = Field(
        None, description="Action IDs that can use this credential"
    )


class CredentialCreate(CredentialBase):
    """Schema for creating a new credential."""

    # Raw credential data that will be encrypted
    credential_data: dict[str, Any] = Field(..., description="The actual credential data to encrypt")

    @field_validator("credential_data")
    @classmethod
    def validate_credential_data(cls, v, info):
        """Validate credential data based on type."""
        # Get credential_type from the data being validated
        credential_type = info.data.get("credential_type") if info.data else None

        if not isinstance(v, dict):
            raise ValueError("credential_data must be a dictionary")

        if credential_type == CredentialType.USERNAME_PASSWORD:
            required_fields = {"username", "password"}
            if not all(field in v for field in required_fields):
                raise ValueError("Username/password credentials require 'username' and 'password' fields")

        elif credential_type == CredentialType.API_KEY:
            if "api_key" not in v:
                raise ValueError("API key credentials require 'api_key' field")

        elif credential_type == CredentialType.OAUTH_TOKEN:
            required_fields = {"access_token"}
            if not all(field in v for field in required_fields):
                raise ValueError("OAuth credentials require 'access_token' field")
            # Optional fields: refresh_token, expires_in, token_type

        elif credential_type == CredentialType.BEARER_TOKEN:
            if "token" not in v:
                raise ValueError("Bearer token credentials require 'token' field")

        elif credential_type == CredentialType.COOKIE_SESSION:
            if "cookies" not in v:
                raise ValueError("Cookie session credentials require 'cookies' field")

        # CUSTOM type allows any structure

        return v


class CredentialUpdate(BaseModel):
    """Schema for updating an existing credential."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] | None = None
    expires_at: datetime | None = None
    access_restricted_to_actions: list[str] | None = None
    is_active: bool | None = None

    # Allow updating credential data
    credential_data: dict[str, Any] | None = Field(None, description="New credential data to encrypt")


class CredentialResponse(CredentialBase):
    """Schema for credential responses (without sensitive data)."""

    id: str
    user_id: str
    is_active: bool
    last_used: datetime | None
    last_validated: datetime | None
    validation_status: str | None
    usage_count: int
    is_expired: bool
    is_valid: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CredentialWithData(CredentialResponse):
    """Schema for credential with decrypted data (for internal use only)."""

    credential_data: dict[str, Any] = Field(..., description="Decrypted credential data")


class CredentialValidationRequest(BaseModel):
    """Schema for credential validation request."""

    credential_id: str = Field(..., description="ID of credential to validate")
    validation_url: str | None = Field(None, description="URL to test credential against")


class CredentialValidationResponse(BaseModel):
    """Schema for credential validation response."""

    credential_id: str
    is_valid: bool
    validation_message: str | None
    validated_at: datetime


class BulkCredentialResponse(BaseModel):
    """Schema for bulk credential operations."""

    success: bool
    message: str
    processed_count: int
    failed_count: int
    credentials: list[CredentialResponse]


class CredentialUsageStats(BaseModel):
    """Schema for credential usage statistics."""

    credential_id: str
    usage_count: int
    last_used: datetime | None
    success_rate: float
    avg_response_time: float | None
    recent_errors: list[str]
