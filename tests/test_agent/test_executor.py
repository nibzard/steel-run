"""Tests for Claude Agent executor."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.agent.executor import ClaudeAgent, BrowserSession


class TestBrowserSession:
    """Test cases for BrowserSession."""
    
    def test_browser_session_init(self):
        """Test BrowserSession initialization."""
        mock_steel = Mock()
        session_id = "test_session_123"
        
        browser = BrowserSession(mock_steel, session_id)
        
        assert browser.steel == mock_steel
        assert browser.session_id == session_id
        assert browser.current_url is None
        assert browser.viewport_size == {"width": 1920, "height": 1080}
    
    async def test_navigate_success(self):
        """Test successful navigation."""
        mock_steel = Mock()
        browser = BrowserSession(mock_steel, "session_123")
        
        url = "https://example.com"
        result = await browser.navigate(url)
        
        assert result is True
        assert browser.current_url == url
    
    @patch('app.agent.executor.base64.b64encode')
    async def test_take_screenshot_success(self, mock_b64encode):
        """Test successful screenshot capture."""
        mock_steel = Mock()
        
        # Mock Steel screenshot response
        mock_screenshot_response = Mock()
        mock_screenshot_response.screenshot.path = "screenshot_path"
        mock_steel.screenshot.return_value = mock_screenshot_response
        
        # Mock file download response
        mock_file_response = Mock()
        mock_file_response.content = b"fake_image_data"
        mock_steel.files.download.return_value = mock_file_response
        
        # Mock base64 encoding
        mock_b64encode.return_value = b"encoded_image_data"
        
        browser = BrowserSession(mock_steel, "session_123")
        browser.current_url = "https://example.com"
        
        result = await browser.take_screenshot()
        
        assert result == "encoded_image_data"
        mock_steel.screenshot.assert_called_once()
        mock_steel.files.download.assert_called_once_with("screenshot_path")
        mock_b64encode.assert_called_once_with(b"fake_image_data")
    
    async def test_take_screenshot_failure(self):
        """Test screenshot failure handling."""
        mock_steel = Mock()
        mock_steel.screenshot.side_effect = Exception("Screenshot failed")
        
        browser = BrowserSession(mock_steel, "session_123")
        result = await browser.take_screenshot()
        
        assert result is None
    
    async def test_scroll_success(self):
        """Test successful scrolling."""
        mock_steel = Mock()
        browser = BrowserSession(mock_steel, "session_123")
        
        result = await browser.scroll("down", 500)
        
        assert result is True
    
    async def test_wait_for_element_success(self):
        """Test successful element wait."""
        mock_steel = Mock()
        browser = BrowserSession(mock_steel, "session_123")
        
        result = await browser.wait_for_element(".test-element", timeout=10)
        
        assert result is True


class TestClaudeAgent:
    """Test cases for ClaudeAgent."""
    
    def test_claude_agent_init(self):
        """Test ClaudeAgent initialization."""
        mock_browser = Mock()
        
        agent = ClaudeAgent(mock_browser)
        
        assert agent.browser == mock_browser
        assert agent.max_iterations == 10
        assert len(agent.blocked_domains) > 0
        assert agent.conversation_history == []
    
    def test_build_system_prompt(self):
        """Test system prompt generation."""
        mock_browser = Mock()
        mock_browser.current_url = "https://example.com"
        mock_browser.session_id = "session_123"
        mock_browser.viewport_size = {"width": 1920, "height": 1080}
        
        agent = ClaudeAgent(mock_browser)
        
        task = "Click the login button"
        context = {"user_id": "123"}
        
        prompt = agent._build_system_prompt(task, context)
        
        assert task in prompt
        assert "session_123" in prompt
        assert "https://example.com" in prompt
        assert "1920x1080" in prompt
        assert '"user_id": "123"' in prompt
        assert "blocked domains" in prompt.lower()
        assert "SECURITY RESTRICTIONS" in prompt
    
    def test_is_url_allowed_safe_urls(self):
        """Test URL safety validation for allowed URLs."""
        mock_browser = Mock()
        agent = ClaudeAgent(mock_browser)
        
        safe_urls = [
            "https://twitter.com",
            "https://x.com", 
            "https://linkedin.com",
            "https://github.com",
            "https://stackoverflow.com",
            "https://example.com"
        ]
        
        for url in safe_urls:
            assert agent._is_url_allowed(url) is True
    
    def test_is_url_allowed_blocked_domains(self):
        """Test URL safety validation for blocked domains."""
        mock_browser = Mock()
        agent = ClaudeAgent(mock_browser)
        
        # Add some blocked domains to the agent
        agent.blocked_domains.add("maliciousbook.com")
        agent.blocked_domains.add("evilsite.com")
        
        blocked_urls = [
            "https://maliciousbook.com/page",
            "https://evilsite.com/hack",
            "http://maliciousbook.com"
        ]
        
        for url in blocked_urls:
            assert agent._is_url_allowed(url) is False
    
    def test_is_url_allowed_invalid_urls(self):
        """Test URL safety validation for invalid URLs."""
        mock_browser = Mock()
        agent = ClaudeAgent(mock_browser)
        
        invalid_urls = [
            "not_a_url",
            "javascript:alert('xss')",
            "",
            None
        ]
        
        for url in invalid_urls:
            if url is not None:
                assert agent._is_url_allowed(url) is False
    
    async def test_navigate_safely_allowed_url(self):
        """Test safe navigation with allowed URL."""
        mock_browser = AsyncMock()
        mock_browser.navigate.return_value = True
        
        agent = ClaudeAgent(mock_browser)
        
        result = await agent.navigate_safely("https://example.com")
        
        assert result is True
        mock_browser.navigate.assert_called_once_with("https://example.com")
    
    async def test_navigate_safely_blocked_url(self):
        """Test safe navigation with blocked URL."""
        mock_browser = AsyncMock()
        
        agent = ClaudeAgent(mock_browser)
        agent.blocked_domains.add("maliciousbook.com")
        
        result = await agent.navigate_safely("https://maliciousbook.com/hack")
        
        assert result is False
        mock_browser.navigate.assert_not_called()
    
    @patch('app.agent.executor.AsyncAnthropic')
    async def test_execute_task_success(self, mock_anthropic_class):
        """Test successful task execution."""
        # Setup mocks
        mock_browser = AsyncMock()
        mock_browser.take_screenshot.return_value = "fake_screenshot_b64"
        mock_browser.session_id = "session_123"
        mock_browser.current_url = "https://example.com"
        
        # Mock Anthropic API
        mock_anthropic = AsyncMock()
        mock_anthropic_class.return_value = mock_anthropic
        
        mock_response = Mock()
        mock_response.content = [Mock(text="Task completed successfully")]
        mock_anthropic.messages.create.return_value = mock_response
        
        agent = ClaudeAgent(mock_browser)
        
        # Execute task
        result = await agent.execute_task("Click the login button")
        
        # Verify result structure
        assert result["status"] == "success"
        assert result["task"] == "Click the login button"
        assert result["session_id"] == "session_123"
        assert "execution_time_ms" in result
        assert "screenshots" in result
        assert "evidence" in result
        assert len(result["screenshots"]) >= 2  # initial and final
        
        # Verify Claude API was called
        mock_anthropic.messages.create.assert_called_once()
    
    @patch('app.agent.executor.AsyncAnthropic')
    async def test_execute_task_failure(self, mock_anthropic_class):
        """Test task execution failure handling."""
        # Setup mocks
        mock_browser = AsyncMock()
        mock_browser.take_screenshot.return_value = None
        mock_browser.session_id = "session_123"
        
        # Mock Anthropic API failure
        mock_anthropic = AsyncMock()
        mock_anthropic_class.return_value = mock_anthropic
        mock_anthropic.messages.create.side_effect = Exception("API Error")
        
        agent = ClaudeAgent(mock_browser)
        
        # Execute task
        result = await agent.execute_task("Click the login button")
        
        # Verify error handling
        assert result["status"] == "failed"
        assert "Task execution error" in result["message"]
        assert "execution_time_ms" in result
        assert result["iterations"] == 0
    
    @patch('app.agent.executor.AsyncAnthropic')
    async def test_execute_with_claude_success(self, mock_anthropic_class):
        """Test Claude execution with proper message formatting."""
        # Setup mocks
        mock_browser = Mock()
        mock_browser.session_id = "session_123"
        
        mock_anthropic = AsyncMock()
        mock_anthropic_class.return_value = mock_anthropic
        
        mock_response = Mock()
        mock_response.content = [Mock(text="I will complete this task step by step")]
        mock_anthropic.messages.create.return_value = mock_response
        
        agent = ClaudeAgent(mock_browser)
        
        # Execute with Claude
        result = await agent._execute_with_claude("Test task", "fake_screenshot_b64")
        
        # Verify result
        assert result["status"] == "success"
        assert "evidence" in result
        assert result["evidence"]["claude_response"] == "I will complete this task step by step"
        
        # Verify API call format
        call_args = mock_anthropic.messages.create.call_args
        assert call_args[1]["model"] == "claude-3-5-sonnet-20241022"
        assert call_args[1]["max_tokens"] == 4096
        
        messages = call_args[1]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert isinstance(messages[0]["content"], list)
        
        # Check message has both text and image
        content = messages[0]["content"]
        has_text = any(item["type"] == "text" for item in content)
        has_image = any(item["type"] == "image" for item in content)
        assert has_text and has_image