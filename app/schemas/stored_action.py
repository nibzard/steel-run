"""Stored action schemas for API operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class StoredActionBase(BaseModel):
    """Base stored action schema with common fields."""

    name: str = Field(max_length=255, description="Human-readable action name")
    description: str | None = Field(None, description="Detailed action description")
    action_type: str = Field(max_length=100, description="Type of base action to execute")
    parameters: dict[str, Any] = Field(description="Action parameters as JSON object")
    webhook_url: HttpUrl | None = Field(None, description="URL to notify on completion")
    is_active: bool = Field(default=True, description="Whether action is active")
    is_public: bool = Field(default=False, description="Whether action is shared publicly")
    tags: list[str] | None = Field(None, description="Tags for categorization")


class StoredActionCreate(StoredActionBase):
    """Schema for creating a new stored action."""

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v):
        """Validate that action type is supported."""
        # For now, accept any string - validation will be done at runtime
        # TODO: Import here to avoid circular imports
        # from ..actions.registry import action_registry
        # if not action_registry.is_registered(v):
        #     raise ValueError(f"Unsupported action type: {v}")
        return v

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v):
        """Validate parameters for the specified action type."""
        # For now, accept any dict - validation will be done at runtime
        # TODO: Import here to avoid circular imports and validate parameters
        # from ..actions.registry import action_registry
        # action_type = values["action_type"]
        # if action_registry.is_registered(action_type):
        #     action_class = action_registry.get_action(action_type)
        #     try:
        #         action_class(**v)
        #     except Exception as e:
        #         raise ValueError(f"Invalid parameters for action type '{action_type}': {str(e)}")

        return v


class StoredActionUpdate(BaseModel):
    """Schema for updating a stored action."""

    name: str | None = Field(None, max_length=255)
    description: str | None = None
    parameters: dict[str, Any] | None = None
    webhook_url: HttpUrl | None = None
    is_active: bool | None = None
    is_public: bool | None = None
    tags: list[str] | None = None

    @field_validator("parameters")
    @classmethod
    def validate_parameters_if_provided(cls, v):
        """Validate parameters if provided."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("Parameters must be a JSON object")
        return v


class StoredActionResponse(StoredActionBase):
    """Schema for stored action API responses."""

    id: str
    user_id: str
    run_count: int
    success_count: int
    failure_count: int
    last_run: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    avg_execution_time: int | None = Field(None, description="Average execution time in milliseconds")
    success_rate: str | None = Field(None, description="Success rate as percentage")
    version: int
    created_at: datetime
    updated_at: datetime
    api_endpoint: str = Field(description="API endpoint URL for this action")

    class Config:
        from_attributes = True


class StoredActionListResponse(BaseModel):
    """Schema for paginated stored action list."""

    actions: list[StoredActionResponse]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
    has_next: bool
    has_previous: bool


class ExecutionRequest(BaseModel):
    """Schema for executing a stored action."""

    input: str | None = Field(None, description="Natural language input for direct execution")
    parameters: dict[str, Any] | None = Field(None, description="Override parameters for this execution")
    webhook_url: HttpUrl | None = Field(None, description="Override webhook URL for this execution")
    timeout_seconds: int | None = Field(30, ge=5, le=300, description="Execution timeout in seconds")
    max_retries: int | None = Field(0, ge=0, le=3, description="Maximum retry attempts")
    external_request_id: str | None = Field(None, max_length=100, description="External service request ID")


class ExecutionResponse(BaseModel):
    """Schema for execution response."""

    run_id: str = Field(description="Unique execution run ID")
    status: str = Field(description="Current execution status")
    message: str = Field(description="Human-readable status message")
    estimated_duration: int | None = Field(None, description="Estimated duration in seconds")
    webhook_url: str | None = Field(None, description="Webhook URL for notifications")


class ExecutionStatus(BaseModel):
    """Schema for execution status response."""

    run_id: str
    action_id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_time: int | None = Field(None, description="Execution time in milliseconds")
    progress: int | None = Field(None, ge=0, le=100, description="Progress percentage")
    error_message: str | None = None
    error_code: str | None = None

    class Config:
        from_attributes = True


class ExecutionResult(BaseModel):
    """Schema for execution results."""

    run_id: str
    action_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    execution_time: int | None = Field(None, description="Execution time in milliseconds")
    result_data: dict[str, Any] | None = Field(None, description="Execution results")
    error_message: str | None = None
    error_code: str | None = None
    screenshot_url: str | None = None
    pdf_url: str | None = None
    session_id: str | None = None
    session_region: str | None = None
    credits_used: int | None = None

    class Config:
        from_attributes = True


class ActionStats(BaseModel):
    """Schema for action statistics."""

    action_id: str
    run_count: int
    success_count: int
    failure_count: int
    success_rate: float | None = Field(None, description="Success rate as decimal")
    avg_execution_time: int | None = Field(None, description="Average execution time in milliseconds")
    last_run: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None


class WebhookPayload(BaseModel):
    """Schema for webhook notifications."""

    event_type: str = Field(description="Event type (execution.started, execution.completed, execution.failed)")
    timestamp: datetime
    run_id: str
    action_id: str
    action_name: str
    status: str
    execution_time: int | None = None
    result_data: dict[str, Any] | None = None
    error_message: str | None = None
    error_code: str | None = None
    external_request_id: str | None = None
