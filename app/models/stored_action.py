"""Stored action model for user-saved web actions."""


from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, UUIDMixin


class StoredAction(Base, UUIDMixin, TimestampMixin):
    """User-saved action configurations for reuse and API integration."""

    __tablename__ = "stored_actions"

    # Ownership
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Basic information
    name = Column(String(255), nullable=False, doc="Human-readable action name")
    description = Column(Text, nullable=True, doc="Detailed action description")
    action_type = Column(String(100), nullable=False, index=True, doc="Type of base action to execute")

    # Configuration
    parameters = Column(Text, nullable=False, doc="JSON-encoded action parameters")
    webhook_url = Column(String(500), nullable=True, doc="URL to notify on completion")

    # Scheduling (future feature)
    schedule = Column(String(100), nullable=True, doc="Cron expression for automated execution")
    is_scheduled = Column(Boolean, default=False, nullable=False)
    next_run = Column(DateTime, nullable=True, doc="Next scheduled execution time")

    # Status and usage
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False, doc="Whether action is shared publicly")
    run_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_run = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)

    # Performance metrics
    avg_execution_time = Column(Integer, nullable=True, doc="Average execution time in milliseconds")
    success_rate = Column(String(10), nullable=True, doc="Success rate as percentage")

    # Metadata
    tags = Column(Text, nullable=True, doc="JSON array of tags for categorization")
    version = Column(Integer, default=1, nullable=False)

    # Relationships
    user = relationship("User", back_populates="stored_actions")
    execution_runs = relationship("ExecutionRun", back_populates="stored_action", cascade="all, delete-orphan")

    @property
    def success_percentage(self) -> float | None:
        """Calculate success rate percentage."""
        if self.run_count == 0:
            return None
        return round((self.success_count / self.run_count) * 100, 1)

    @property
    def api_endpoint(self) -> str:
        """Get the API endpoint URL for this stored action."""
        return f"/api/actions/{self.id}/run"

    def update_stats(self, success: bool, execution_time: int) -> None:
        """
        Update action statistics after execution.

        Args:
            success: Whether the execution was successful
            execution_time: Execution time in milliseconds
        """
        self.run_count += 1
        self.last_run = func.now()

        if success:
            self.success_count += 1
            self.last_success = func.now()
        else:
            self.failure_count += 1
            self.last_failure = func.now()

        # Update average execution time
        if self.avg_execution_time is None:
            self.avg_execution_time = execution_time
        else:
            # Running average calculation
            self.avg_execution_time = int(
                (self.avg_execution_time * (self.run_count - 1) + execution_time) / self.run_count
            )

        # Update success rate string for easy display
        self.success_rate = f"{self.success_percentage}%" if self.success_percentage is not None else None

    def __repr__(self) -> str:
        return f"<StoredAction(id='{self.id}', name='{self.name}', type='{self.action_type}')>"
