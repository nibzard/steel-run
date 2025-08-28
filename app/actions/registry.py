"""Action registry for managing and discovering atomic web actions."""


import structlog

from .base import BaseAction

logger = structlog.get_logger(__name__)


class ActionRegistry:
    """Registry for managing atomic web actions."""

    def __init__(self):
        self._actions: dict[str, type[BaseAction]] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, action_id: str, action_class: type[BaseAction]) -> None:
        """
        Register an action class with the registry.

        Args:
            action_id: Unique identifier for the action
            action_class: BaseAction subclass to register
        """
        if not issubclass(action_class, BaseAction):
            raise ValueError(f"Action class must inherit from BaseAction: {action_class}")

        if action_id in self._actions:
            logger.warning("Action ID already registered, overwriting", action_id=action_id)

        self._actions[action_id] = action_class

        # Update category index
        action_instance = action_class()
        category = action_instance.category

        if category not in self._categories:
            self._categories[category] = []

        if action_id not in self._categories[category]:
            self._categories[category].append(action_id)

        logger.info(
            "Action registered successfully",
            action_id=action_id,
            action_name=action_instance.name,
            category=category,
        )

    def get(self, action_id: str) -> type[BaseAction] | None:
        """
        Get an action class by ID.

        Args:
            action_id: Action identifier

        Returns:
            BaseAction subclass or None if not found
        """
        return self._actions.get(action_id)

    def create_instance(self, action_id: str) -> BaseAction | None:
        """
        Create an instance of the specified action.

        Args:
            action_id: Action identifier

        Returns:
            BaseAction instance or None if not found
        """
        action_class = self.get(action_id)
        if action_class:
            return action_class()
        return None

    def list_actions(self, category: str | None = None, tags: list[str] | None = None) -> list[dict]:
        """
        List registered actions with optional filtering.

        Args:
            category: Optional category filter
            tags: Optional tags filter (action must have all specified tags)

        Returns:
            List of action metadata dictionaries
        """
        actions = []

        for action_id, action_class in self._actions.items():
            # Skip if category filter doesn't match
            if category:
                action_instance = action_class()
                if action_instance.category != category:
                    continue

            # Skip if tags filter doesn't match
            if tags:
                action_instance = action_class()
                if not all(tag in action_instance.tags for tag in tags):
                    continue

            # Add action metadata
            action_instance = action_class()
            metadata = action_instance.get_metadata()
            metadata["id"] = action_id
            actions.append(metadata)

        # Sort by name for consistent ordering
        actions.sort(key=lambda x: x["name"])
        return actions

    def get_categories(self) -> dict[str, list[str]]:
        """
        Get all categories and their associated action IDs.

        Returns:
            Dict mapping category names to lists of action IDs
        """
        return self._categories.copy()

    def search(self, query: str) -> list[dict]:
        """
        Search for actions by name, description, or tags.

        Args:
            query: Search query string

        Returns:
            List of matching action metadata dictionaries
        """
        query_lower = query.lower()
        matches = []

        for action_id, action_class in self._actions.items():
            action_instance = action_class()

            # Check name
            if query_lower in action_instance.name.lower():
                metadata = action_instance.get_metadata()
                metadata["id"] = action_id
                metadata["match_reason"] = "name"
                matches.append(metadata)
                continue

            # Check description
            if query_lower in action_instance.description.lower():
                metadata = action_instance.get_metadata()
                metadata["id"] = action_id
                metadata["match_reason"] = "description"
                matches.append(metadata)
                continue

            # Check tags
            if any(query_lower in tag.lower() for tag in action_instance.tags):
                metadata = action_instance.get_metadata()
                metadata["id"] = action_id
                metadata["match_reason"] = "tags"
                matches.append(metadata)
                continue

        # Sort by relevance (name matches first, then description, then tags)
        def sort_key(action):
            order = {"name": 0, "description": 1, "tags": 2}
            return (order.get(action.get("match_reason", "tags"), 2), action["name"])

        matches.sort(key=sort_key)
        return matches

    def get_popular_actions(self, limit: int = 10) -> list[dict]:
        """
        Get popular actions (for now, just returns all actions limited).

        In the future, this could be based on usage statistics.

        Args:
            limit: Maximum number of actions to return

        Returns:
            List of action metadata dictionaries
        """
        all_actions = self.list_actions()
        return all_actions[:limit]

    def validate_action_id(self, action_id: str) -> bool:
        """
        Check if an action ID is registered.

        Args:
            action_id: Action identifier to check

        Returns:
            bool: True if action is registered
        """
        return action_id in self._actions

    def get_action_count(self) -> int:
        """
        Get total number of registered actions.

        Returns:
            int: Number of registered actions
        """
        return len(self._actions)


# Global registry instance
_action_registry = ActionRegistry()


def get_action_registry() -> ActionRegistry:
    """
    Get the global action registry instance.

    Returns:
        ActionRegistry: The global registry
    """
    return _action_registry


def register_action(action_id: str, action_class: type[BaseAction]) -> None:
    """
    Convenience function to register an action with the global registry.

    Args:
        action_id: Unique identifier for the action
        action_class: BaseAction subclass to register
    """
    _action_registry.register(action_id, action_class)


# Auto-discovery function for loading actions from modules
def discover_actions(module_names: list[str]) -> None:
    """
    Discover and register actions from specified modules.

    Args:
        module_names: List of module names to search for actions
    """
    import importlib
    import inspect

    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)

            # Find all BaseAction subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseAction) and
                    obj != BaseAction and
                    hasattr(obj, 'name') and
                    obj.name != "Base Action"):

                    # Generate action ID from class name
                    action_id = name.lower().replace('action', '').replace('_', '-')
                    if not action_id.endswith('-action'):
                        action_id = f"{action_id}-action"

                    register_action(action_id, obj)

        except ImportError as e:
            logger.warning("Failed to import action module", module=module_name, error=str(e))
        except Exception as e:
            logger.error("Error during action discovery", module=module_name, error=str(e))
