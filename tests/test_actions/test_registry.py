"""Tests for action registry."""

import pytest
from unittest.mock import MagicMock, patch

from app.actions.registry import ActionRegistry, get_action_registry, register_action
from app.actions.base import BaseAction
from app.actions.website import WebsiteScreenshotAction, WebsiteContentAction


class MockAction(BaseAction):
    """Mock action for testing."""
    
    name = "Mock Action"
    description = "A mock action for testing"
    category = "mock"
    tags = ["test", "mock"]
    
    parameters = {
        "test_param": {"type": "string", "required": True}
    }
    
    async def execute(self, **params):
        return {"status": "success", "message": "Mock executed"}


@pytest.fixture
def registry():
    """Create a fresh registry for testing."""
    return ActionRegistry()


def test_registry_register_action(registry):
    """Test registering an action."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        
        assert registry.validate_action_id("mock-action")
        assert registry.get_action_count() == 1


def test_registry_get_action(registry):
    """Test retrieving an action class."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        
        action_class = registry.get("mock-action")
        assert action_class == MockAction
        
        # Test non-existent action
        assert registry.get("non-existent") is None


def test_registry_create_instance(registry):
    """Test creating action instances."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        
        instance = registry.create_instance("mock-action")
        assert isinstance(instance, MockAction)
        
        # Test non-existent action
        assert registry.create_instance("non-existent") is None


def test_registry_list_actions(registry):
    """Test listing all actions."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        registry.register("screenshot-action", WebsiteScreenshotAction)
        
        actions = registry.list_actions()
        assert len(actions) == 2
        
        # Check that actions are sorted by name
        names = [action["name"] for action in actions]
        assert names == sorted(names)
        
        # Check metadata structure
        action = actions[0]
        assert "id" in action
        assert "name" in action
        assert "description" in action
        assert "parameters" in action


def test_registry_list_actions_with_category_filter(registry):
    """Test listing actions with category filter."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        registry.register("screenshot-action", WebsiteScreenshotAction)
        
        # Filter by 'website' category
        website_actions = registry.list_actions(category="website")
        assert len(website_actions) == 1
        assert website_actions[0]["name"] == "Website Screenshot"
        
        # Filter by 'mock' category
        mock_actions = registry.list_actions(category="mock")
        assert len(mock_actions) == 1
        assert mock_actions[0]["name"] == "Mock Action"
        
        # Filter by non-existent category
        empty_actions = registry.list_actions(category="nonexistent")
        assert len(empty_actions) == 0


def test_registry_search(registry):
    """Test searching for actions."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        registry.register("screenshot-action", WebsiteScreenshotAction)
        registry.register("content-action", WebsiteContentAction)
        
        # Search by name
        results = registry.search("mock")
        assert len(results) == 1
        assert results[0]["name"] == "Mock Action"
        assert results[0]["match_reason"] == "name"
        
        # Search by description/tag
        results = registry.search("screenshot")
        assert len(results) >= 1
        screenshot_result = next(r for r in results if "Screenshot" in r["name"])
        assert "screenshot" in screenshot_result["tags"]
        
        # Search with no matches
        results = registry.search("nonexistent")
        assert len(results) == 0


def test_registry_get_categories(registry):
    """Test getting category information."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        registry.register("screenshot-action", WebsiteScreenshotAction)
        
        categories = registry.get_categories()
        assert "mock" in categories
        assert "website" in categories
        assert "mock-action" in categories["mock"]
        assert "screenshot-action" in categories["website"]


def test_registry_get_popular_actions(registry):
    """Test getting popular actions."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        registry.register("mock-action", MockAction)
        registry.register("screenshot-action", WebsiteScreenshotAction)
        
        popular = registry.get_popular_actions(limit=1)
        assert len(popular) == 1
        
        popular_all = registry.get_popular_actions()
        assert len(popular_all) == 2


def test_global_registry():
    """Test global registry functions."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        
        # Get global registry
        global_registry = get_action_registry()
        assert isinstance(global_registry, ActionRegistry)
        
        # Register action using convenience function
        initial_count = global_registry.get_action_count()
        register_action("test-mock-action", MockAction)
        
        assert global_registry.get_action_count() == initial_count + 1
        assert global_registry.validate_action_id("test-mock-action")


def test_registry_invalid_action_class():
    """Test registering invalid action class."""
    registry = ActionRegistry()
    
    class NotAnAction:
        pass
    
    with pytest.raises(ValueError) as exc_info:
        registry.register("invalid", NotAnAction)
    
    assert "must inherit from BaseAction" in str(exc_info.value)