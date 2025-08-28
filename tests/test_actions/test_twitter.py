"""Tests for Twitter actions."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.actions.twitter import TwitterPostAction, TwitterReplyAction
from app.actions.base import ActionValidationError


class TestTwitterPostAction:
    """Test cases for TwitterPostAction."""
    
    def test_action_metadata(self):
        """Test action metadata is properly configured."""
        action = TwitterPostAction()
        
        assert action.name == "Post to Twitter"
        assert action.description == "Post a tweet to your Twitter timeline"
        assert action.category == "social_media"
        assert "twitter" in action.tags
        assert action.requires_auth is True
        assert action.timeout_seconds == 60
    
    def test_parameter_validation_valid_message(self):
        """Test parameter validation with valid message."""
        action = TwitterPostAction()
        
        params = {
            "message": "Hello, World!",
            "credentials": {"username": "test", "password": "test123"}
        }
        
        # Should not raise any exception
        action.validate_parameters(params)
    
    def test_parameter_validation_message_too_long(self):
        """Test parameter validation with message exceeding 280 characters."""
        action = TwitterPostAction()
        
        # Create a message longer than 280 characters
        long_message = "x" * 281
        
        params = {
            "message": long_message,
            "credentials": {"username": "test", "password": "test123"}
        }
        
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        
        assert "exceeds maximum length" in str(exc_info.value)
    
    def test_parameter_validation_missing_message(self):
        """Test parameter validation with missing message."""
        action = TwitterPostAction()
        
        params = {
            "credentials": {"username": "test", "password": "test123"}
        }
        
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        
        assert "Required parameter 'message' missing" in str(exc_info.value)
    
    def test_parameter_validation_empty_message(self):
        """Test parameter validation with empty message."""
        action = TwitterPostAction()
        
        params = {
            "message": "",
            "credentials": {"username": "test", "password": "test123"}
        }
        
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        
        assert "must be at least 1 characters" in str(exc_info.value)
    
    def test_task_description_generation(self):
        """Test task description generation for Claude."""
        action = TwitterPostAction()
        
        message = "Test tweet message"
        credentials = {"username": "testuser", "password": "testpass"}
        
        task_desc = action._build_task_description(message, credentials, True)
        
        assert "x.com" in task_desc
        assert message in task_desc
        assert "testuser" in task_desc
        assert "280 character limit" in task_desc
        assert "VERIFY the tweet was posted" in task_desc
    
    @patch('app.actions.twitter.ClaudeAgent')
    @patch('app.actions.twitter.BrowserSession')
    async def test_execute_success(self, mock_browser_session, mock_claude_agent):
        """Test successful tweet posting execution."""
        # Setup mocks
        mock_agent_instance = AsyncMock()
        mock_claude_agent.return_value = mock_agent_instance
        
        mock_agent_instance.execute_task.return_value = {
            "status": "success",
            "message": "Tweet posted successfully",
            "screenshots": [{"image_b64": "fake_screenshot"}],
            "evidence": {"claude_response": "Task completed"}
        }
        
        action = TwitterPostAction()
        action.create_session = AsyncMock(return_value="session_123")
        action.capture_screenshot = AsyncMock(return_value="screenshot_url")
        
        # Execute action
        result = await action.execute(
            message="Test tweet",
            credentials={"username": "test", "password": "test123"}
        )
        
        # Verify result
        assert result["status"] == "success"
        assert "Successfully posted tweet" in result["message"]
        assert result["data"]["tweet_message"] == "Test tweet"
        assert result["data"]["message_length"] == 10


class TestTwitterReplyAction:
    """Test cases for TwitterReplyAction."""
    
    def test_action_metadata(self):
        """Test action metadata is properly configured."""
        action = TwitterReplyAction()
        
        assert action.name == "Reply to Twitter Post"
        assert action.description == "Reply to a specific tweet on Twitter"
        assert action.category == "social_media"
        assert "reply" in action.tags
        assert action.requires_auth is True
    
    def test_parameter_validation_valid_params(self):
        """Test parameter validation with valid parameters."""
        action = TwitterReplyAction()
        
        params = {
            "tweet_url": "https://twitter.com/user/status/123456789",
            "reply_message": "Great point!",
            "credentials": {"username": "test", "password": "test123"}
        }
        
        # Should not raise any exception
        action.validate_parameters(params)
    
    def test_parameter_validation_missing_tweet_url(self):
        """Test parameter validation with missing tweet URL."""
        action = TwitterReplyAction()
        
        params = {
            "reply_message": "Great point!",
            "credentials": {"username": "test", "password": "test123"}
        }
        
        with pytest.raises(ActionValidationError) as exc_info:
            action.validate_parameters(params)
        
        assert "Required parameter 'tweet_url' missing" in str(exc_info.value)
    
    def test_tweet_url_validation_valid_urls(self):
        """Test tweet URL validation with valid URLs."""
        action = TwitterReplyAction()
        
        valid_urls = [
            "https://twitter.com/user/status/123456789",
            "https://x.com/user/status/987654321",
            "https://twitter.com/elonmusk/status/123456789012345678",
            "https://x.com/openai/status/123456789012345678"
        ]
        
        for url in valid_urls:
            assert action._is_valid_tweet_url(url) is True
    
    def test_tweet_url_validation_invalid_urls(self):
        """Test tweet URL validation with invalid URLs."""
        action = TwitterReplyAction()
        
        invalid_urls = [
            "https://facebook.com/post/123",
            "https://linkedin.com/posts/123",
            "https://instagram.com/p/abc123",
            "https://google.com",
            "not_a_url_at_all"
        ]
        
        for url in invalid_urls:
            assert action._is_valid_tweet_url(url) is False
    
    def test_reply_task_description_generation(self):
        """Test reply task description generation for Claude."""
        action = TwitterReplyAction()
        
        tweet_url = "https://twitter.com/user/status/123456789"
        reply_message = "Thanks for sharing!"
        credentials = {"username": "testuser", "password": "testpass"}
        
        task_desc = action._build_reply_task_description(
            tweet_url, reply_message, credentials
        )
        
        assert tweet_url in task_desc
        assert reply_message in task_desc
        assert "testuser" in task_desc
        assert "reply button" in task_desc
        assert "specific tweet" in task_desc
    
    @patch('app.actions.twitter.ClaudeAgent')
    @patch('app.actions.twitter.BrowserSession')
    async def test_execute_success(self, mock_browser_session, mock_claude_agent):
        """Test successful tweet reply execution."""
        # Setup mocks
        mock_agent_instance = AsyncMock()
        mock_claude_agent.return_value = mock_agent_instance
        
        mock_agent_instance.execute_task.return_value = {
            "status": "success", 
            "message": "Reply posted successfully",
            "screenshots": [{"image_b64": "fake_screenshot"}],
            "evidence": {"claude_response": "Reply completed"}
        }
        
        action = TwitterReplyAction()
        action.create_session = AsyncMock(return_value="session_123")
        action.capture_screenshot = AsyncMock(return_value="screenshot_url")
        
        # Execute action
        result = await action.execute(
            tweet_url="https://twitter.com/user/status/123456789",
            reply_message="Great insight!",
            credentials={"username": "test", "password": "test123"}
        )
        
        # Verify result
        assert result["status"] == "success"
        assert "Successfully replied to tweet" in result["message"]
        assert result["data"]["original_tweet_url"] == "https://twitter.com/user/status/123456789"
        assert result["data"]["reply_message"] == "Great insight!"
        assert result["data"]["reply_length"] == 14
    
    async def test_execute_invalid_tweet_url(self):
        """Test execution with invalid tweet URL."""
        action = TwitterReplyAction()
        
        with pytest.raises(ActionValidationError) as exc_info:
            await action.execute(
                tweet_url="https://facebook.com/post/123",
                reply_message="Test reply",
                credentials={"username": "test", "password": "test123"}
            )
        
        assert "Invalid Twitter URL provided" in str(exc_info.value)