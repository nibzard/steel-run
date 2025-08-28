"""Atomic web action implementations."""

from .base import BaseAction
from .registry import ActionRegistry, get_action_registry

__all__ = [
    "BaseAction",
    "ActionRegistry",
    "get_action_registry",
]
