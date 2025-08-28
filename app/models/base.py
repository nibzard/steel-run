"""Base model classes with common functionality."""

import uuid
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.sql import func


@as_declarative()
class Base:
    """Base class for all database models."""

    id: Any
    __name__: str

    # Generate table names automatically
    @declared_attr
    def __tablename__(self) -> str:
        return self.__name__.lower()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when record was created"
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when record was last updated"
    )


class UUIDMixin:
    """Mixin to add UUID primary key."""

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique identifier for the record"
    )


def generate_id(prefix: str = "") -> str:
    """
    Generate a prefixed UUID for consistent ID formatting.

    Args:
        prefix: Optional prefix for the ID (e.g., 'user_', 'action_')

    Returns:
        str: Formatted ID with prefix
    """
    return f"{prefix}{str(uuid.uuid4())}" if prefix else str(uuid.uuid4())
