"""Execution run model for tracking individual action executions."""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin


class ExecutionStatus(str, Enum):
    """Enumeration of execution statuses."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionRun(Base, UUIDMixin, TimestampMixin):
    """Individual execution run tracking for stored actions."""

    __tablename__ = "execution_runs"

    # Relationships
    stored_action_id = Column(String, ForeignKey("stored_actions.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Execution details
    status = Column(String(20), default=ExecutionStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time = Column(Integer, nullable=True, doc="Execution time in milliseconds")

    # Input and output
    input_parameters = Column(Text, nullable=True, doc="JSON-encoded input parameters used")
    result_data = Column(Text, nullable=True, doc="JSON-encoded execution results")
    error_message = Column(Text, nullable=True, doc="Error message if execution failed")
    error_code = Column(String(50), nullable=True, doc="Structured error code")

    # Steel session information
    session_id = Column(String(100), nullable=True, doc="Steel browser session ID")
    session_region = Column(String(10), nullable=True, doc="Steel session region")
    credits_used = Column(Integer, nullable=True, doc="Steel credits consumed")

    # Outputs
    screenshot_url = Column(String(500), nullable=True, doc="URL to execution screenshot")
    screenshot_data = Column(Text, nullable=True, doc="Base64 encoded screenshot data")
    pdf_url = Column(String(500), nullable=True, doc="URL to generated PDF")

    # External integration
    triggered_by = Column(String(20), default="manual", nullable=False, doc="How execution was triggered")
    external_request_id = Column(String(100), nullable=True, doc="External service request ID")
    webhook_sent = Column(Boolean, default=False, nullable=False)
    webhook_response_code = Column(Integer, nullable=True)
    webhook_attempts = Column(Integer, default=0, nullable=False)

    # Performance and reliability
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=0, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)

    # Relationships
    stored_action = relationship("StoredAction", back_populates="execution_runs")
    user = relationship("User")

    @property
    def duration_ms(self) -> int | None:
        """Calculate execution duration in milliseconds."""
        if not self.started_at or not self.completed_at:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)

    @property
    def is_running(self) -> bool:
        """Check if execution is currently running."""
        return self.status in [ExecutionStatus.PENDING, ExecutionStatus.EXECUTING]

    @property
    def is_finished(self) -> bool:
        """Check if execution has finished (success or failure)."""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT
        ]

    @property
    def is_successful(self) -> bool:
        """Check if execution completed successfully."""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def can_retry(self) -> bool:
        """Check if execution can be retried."""
        return (
            self.status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT] and
            self.retry_count < self.max_retries
        )

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.EXECUTING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result_data: dict[str, Any] | None = None) -> None:
        """
        Mark execution as completed successfully.

        Args:
            result_data: Optional result data to store
        """
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.execution_time = self.duration_ms

        if result_data:
            import json
            self.result_data = json.dumps(result_data)

    def mark_failed(self, error_message: str, error_code: str | None = None) -> None:
        """
        Mark execution as failed.

        Args:
            error_message: Human-readable error message
            error_code: Optional structured error code
        """
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.execution_time = self.duration_ms
        self.error_message = error_message
        self.error_code = error_code

    def mark_timeout(self) -> None:
        """Mark execution as timed out."""
        self.status = ExecutionStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.execution_time = self.duration_ms
        self.error_message = f"Execution timed out after {self.timeout_seconds} seconds"
        self.error_code = "TIMEOUT"

    def __repr__(self) -> str:
        return f"<ExecutionRun(id='{self.id}', action='{self.stored_action_id}', status='{self.status}')>"
