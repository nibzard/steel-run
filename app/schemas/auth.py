"""Authentication and user schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    default_region: str = Field(default="lax", description="Default Steel region")
    enable_screenshots: bool = Field(default=True, description="Enable screenshots by default")
    enable_webhooks: bool = Field(default=True, description="Enable webhooks by default")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8, description="User password (min 8 characters)")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        from ..utils.auth import validate_password_strength

        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    username: str | None = None
    full_name: str | None = None
    default_region: str | None = None
    enable_screenshots: bool | None = None
    enable_webhooks: bool | None = None


class UserResponse(UserBase):
    """Schema for user API responses."""

    id: str
    is_active: bool
    is_verified: bool
    total_actions_run: int
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # Subject (user ID)
    email: str
    exp: datetime
    iat: datetime
    type: str = "access"


class APIKeyBase(BaseModel):
    """Base API key schema."""

    name: str = Field(max_length=100, description="Human-readable name for the key")
    rate_limit_per_hour: int = Field(default=500, ge=1, le=10000, description="Rate limit per hour")
    expires_at: datetime | None = Field(None, description="Optional expiration date")


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key."""
    pass


class APIKeyResponse(APIKeyBase):
    """Schema for API key responses."""

    id: str
    key_prefix: str = Field(description="First few characters for identification")
    is_active: bool
    last_used: datetime | None = None
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyGenerated(APIKeyResponse):
    """Schema for newly generated API key (includes full key)."""

    api_key: str = Field(description="Full API key (only shown once)")


class PasswordReset(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        from ..utils.auth import validate_password_strength

        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class PasswordChange(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        from ..utils.auth import validate_password_strength

        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v
