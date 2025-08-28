"""Tests for BaseAction framework."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.actions.base import BaseAction, ActionValidationError, ActionExecutionError
from app.actions.website import WebsiteScreenshotAction, WebsiteContentAction


class TestAction(BaseAction):
    """Simple test action for testing the framework."""
    
    name = "Test Action"
    description = "A test action for unit tests"
    category = "test"
    tags = ["test", "mock"]
    
    parameters = {
        "message": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 100,
        },
        "count": {
            "type": "integer",
            "required": False,
            "min_value": 1,
            "max_value": 10,
        }
    }
    
    async def execute(self, **params):
        """Simple test execution."""
        message = params["message"]
        count = params.get("count", 1)
        
        return {
            "status": "success",
            "message": f"Test executed with: {message}",
            "data": {
                "message": message,
                "count": count,
                "repeated": message * count,
            }
        }


@pytest.fixture
def test_action():
    """Create a test action instance."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = TestAction()
        return action


@pytest.mark.asyncio
async def test_parameter_validation_success(test_action):
    """Test successful parameter validation."""
    params = {"message": "hello world", "count": 3}
    
    # Should not raise any exception
    test_action.validate_parameters(params)


@pytest.mark.asyncio
async def test_parameter_validation_missing_required():
    """Test validation with missing required parameter."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = TestAction()
        
        params = {"count": 3}  # Missing required 'message'
        
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        
        assert "Required parameter 'message' missing" in str(exc_info.value)
        assert exc_info.value.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_parameter_validation_wrong_type():
    """Test validation with wrong parameter type."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = TestAction()
        
        params = {"message": 123}  # Should be string
        
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        
        assert "must be a string" in str(exc_info.value)


@pytest.mark.asyncio
async def test_parameter_validation_length_constraints():
    """Test string length validation."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = TestAction()
        
        # Test minimum length
        params = {"message": ""}  # Too short
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        assert "at least" in str(exc_info.value)
        
        # Test maximum length
        params = {"message": "x" * 101}  # Too long
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        assert "exceeds maximum length" in str(exc_info.value)


@pytest.mark.asyncio
async def test_parameter_validation_integer_constraints():
    """Test integer range validation."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = TestAction()
        
        # Test minimum value
        params = {"message": "hello", "count": 0}  # Too small
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        assert "must be at least" in str(exc_info.value)
        
        # Test maximum value
        params = {"message": "hello", "count": 11}  # Too large
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        assert "must be at most" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_safely_success(test_action):
    """Test successful execution with execute_safely."""
    params = {"message": "test", "count": 2}
    
    # Mock session creation and release
    test_action.create_session = AsyncMock(return_value="test-session-id")
    test_action.release_session = AsyncMock()
    
    result = await test_action.execute_safely(**params)
    
    assert result["status"] == "success"
    assert "Test executed with: test" in result["message"]
    assert result["data"]["repeated"] == "testtest"
    assert "timestamp" in result
    assert "execution_time_ms" in result


@pytest.mark.asyncio
async def test_execute_safely_validation_error(test_action):
    """Test execute_safely with validation error."""
    params = {"message": ""}  # Invalid - too short
    
    result = await test_action.execute_safely(**params)
    
    assert result["status"] == "failed"
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "at least" in result["message"]


@pytest.mark.asyncio 
async def test_get_metadata():
    """Test action metadata retrieval."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = TestAction()
        
        metadata = action.get_metadata()
        
        assert metadata["name"] == "Test Action"
        assert metadata["description"] == "A test action for unit tests"
        assert metadata["category"] == "test"
        assert metadata["tags"] == ["test", "mock"]
        assert metadata["requires_auth"] is False
        assert "parameters" in metadata


@pytest.mark.asyncio
async def test_website_screenshot_action():
    """Test WebsiteScreenshotAction validation and metadata."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = WebsiteScreenshotAction()
        
        # Test metadata
        metadata = action.get_metadata()
        assert metadata["name"] == "Website Screenshot"
        assert metadata["category"] == "website"
        assert "screenshot" in metadata["tags"]
        
        # Test parameter validation
        valid_params = {"url": "https://example.com"}
        action.validate_parameters(valid_params)  # Should not raise
        
        # Test invalid parameters
        with pytest.raises(ActionValidationError):
            action.validate_parameters({})  # Missing required url


@pytest.mark.asyncio
async def test_website_content_action():
    """Test WebsiteContentAction validation and metadata."""
    with patch('app.actions.base.Steel') as mock_steel:
        mock_steel.return_value = MagicMock()
        action = WebsiteContentAction()
        
        # Test metadata
        metadata = action.get_metadata()
        assert metadata["name"] == "Website Content"
        assert metadata["category"] == "website"
        assert "scraping" in metadata["tags"]
        
        # Test parameter validation
        valid_params = {"url": "https://example.com", "format": "text"}
        action.validate_parameters(valid_params)  # Should not raise