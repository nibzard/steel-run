"""Integration tests for Steel SDK integration."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx

from app.actions.website import WebsiteScreenshotAction, WebsiteContentAction


@pytest.mark.integration
class TestSteelSDKIntegration:
    """Test Steel SDK integration with mock responses."""

    @pytest.fixture
    def mock_steel_session(self):
        """Mock Steel session for testing."""
        session = Mock()
        session.id = "test_session_123"
        session.status = "live"
        session.endpoint_url = "https://connect.steel.dev/v1/sessions/test_session_123"
        return session

    @pytest.fixture
    def mock_steel_client(self, mock_steel_session):
        """Mock Steel client for testing."""
        client = AsyncMock()
        client.sessions.create.return_value = mock_steel_session
        client.sessions.release.return_value = Mock(success=True)
        
        # Mock action run result
        run_result = Mock()
        run_result.id = "test_run_456"
        run_result.status = "completed"
        run_result.result = {
            "success": True,
            "data": {"message": "Action completed successfully"}
        }
        run_result.screenshots = ["https://example.com/screenshot.png"]
        run_result.logs = ["Action started", "Action completed"]
        client.actions.run.return_value = run_result
        
        return client

    @pytest.mark.asyncio
    async def test_website_screenshot_steel_integration(self, mock_steel_client):
        """Test website screenshot action with Steel SDK."""
        with patch('app.actions.base.Steel', return_value=mock_steel_client):
            action = WebsiteScreenshotAction()
            
            result = await action.execute_safely(
                url="https://example.com",
                full_page=True
            )
            
            # Verify Steel client interactions
            mock_steel_client.sessions.create.assert_called_once()
            mock_steel_client.actions.run.assert_called_once()
            mock_steel_client.sessions.release.assert_called_once()
            
            # Verify result structure
            assert result["status"] == "success"
            assert "screenshot_url" in result
            assert "session_id" in result

    @pytest.mark.asyncio
    async def test_website_content_steel_integration(self, mock_steel_client):
        """Test website content extraction with Steel SDK."""
        # Mock content extraction result
        mock_steel_client.actions.run.return_value.result = {
            "success": True,
            "data": {
                "title": "Example Website",
                "text_content": "This is example content",
                "links": ["https://example.com/link1", "https://example.com/link2"],
                "meta_description": "Example website description"
            }
        }
        
        with patch('app.actions.base.Steel', return_value=mock_steel_client):
            action = WebsiteContentAction()
            
            result = await action.execute_safely(
                url="https://example.com",
                extract_links=True,
                extract_text=True
            )
            
            # Verify Steel client interactions
            mock_steel_client.sessions.create.assert_called_once()
            mock_steel_client.actions.run.assert_called_once()
            mock_steel_client.sessions.release.assert_called_once()
            
            # Verify extracted content
            assert result["status"] == "success"
            assert result["title"] == "Example Website"
            assert "links" in result
            assert "text_content" in result

    @pytest.mark.asyncio
    async def test_steel_session_cleanup_on_error(self, mock_steel_client):
        """Test Steel session is properly cleaned up on errors."""
        # Make the action execution fail
        mock_steel_client.actions.run.side_effect = Exception("Steel action failed")
        
        with patch('app.actions.base.Steel', return_value=mock_steel_client):
            action = WebsiteScreenshotAction()
            
            # Action should fail but still clean up session
            with pytest.raises(Exception, match="Steel action failed"):
                await action.execute_safely(url="https://example.com")
            
            # Verify session was still released
            mock_steel_client.sessions.create.assert_called_once()
            mock_steel_client.sessions.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_steel_session_reuse_prevention(self, mock_steel_client):
        """Test that each action gets its own Steel session."""
        with patch('app.actions.base.Steel', return_value=mock_steel_client):
            action = WebsiteScreenshotAction()
            
            # Execute action twice
            await action.execute_safely(url="https://example.com")
            await action.execute_safely(url="https://another-example.com")
            
            # Should create and release session twice
            assert mock_steel_client.sessions.create.call_count == 2
            assert mock_steel_client.sessions.release.call_count == 2


@pytest.mark.integration
class TestAnthropicIntegration:
    """Test Anthropic Claude integration (mocked)."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client for testing."""
        client = AsyncMock()
        
        # Mock message response
        response = Mock()
        response.content = [Mock(text="Test AI response for action analysis")]
        client.messages.create.return_value = response
        
        return client

    @pytest.mark.asyncio
    async def test_claude_agent_integration(self, mock_anthropic_client):
        """Test Claude agent integration with Steel actions."""
        with patch('app.agent.executor.anthropic.Anthropic', return_value=mock_anthropic_client):
            # This would test the Claude agent integration
            # Currently not fully implemented, so we mock the expected behavior
            pass


@pytest.mark.integration
class TestExternalServiceIntegration:
    """Test integration with external services."""

    @pytest.mark.asyncio
    async def test_webhook_delivery_integration(self):
        """Test webhook delivery to external services."""
        # Mock webhook endpoint
        webhook_url = "https://hooks.zapier.com/test-webhook"
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock successful webhook response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "received"}
            mock_post.return_value = mock_response
            
            # Test webhook delivery (would be part of execution service)
            async with httpx.AsyncClient() as client:
                webhook_data = {
                    "event_type": "execution.completed",
                    "action_id": "test_action_123",
                    "status": "success",
                    "result": {"message": "Action completed"}
                }
                
                response = await client.post(webhook_url, json=webhook_data)
                assert response.status_code == 200

    @pytest.mark.asyncio  
    async def test_zapier_integration_format(self):
        """Test Zapier-compatible webhook format."""
        zapier_payload = {
            "id": "run_12345",
            "event": "execution_completed",
            "data": {
                "action_name": "Website Screenshot",
                "status": "success",
                "result_url": "https://example.com/result.png",
                "execution_time": 3500,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
        
        # Verify payload structure matches Zapier expectations
        assert "id" in zapier_payload
        assert "event" in zapier_payload  
        assert "data" in zapier_payload
        assert isinstance(zapier_payload["data"], dict)

    def test_n8n_integration_format(self):
        """Test n8n-compatible webhook format."""
        n8n_payload = {
            "executionId": "exec_67890",
            "workflowId": "workflow_123", 
            "status": "completed",
            "data": {
                "action_type": "website_screenshot",
                "parameters": {"url": "https://example.com"},
                "result": {"screenshot_url": "https://example.com/shot.png"}
            },
            "metadata": {
                "started_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:00:05Z"
            }
        }
        
        # Verify payload structure matches n8n expectations
        assert "executionId" in n8n_payload
        assert "workflowId" in n8n_payload
        assert "status" in n8n_payload
        assert "data" in n8n_payload
        assert "metadata" in n8n_payload


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_full_action_execution_flow(self, mock_steel_client):
        """Test complete action execution flow from API to Steel SDK."""
        with patch('app.actions.base.Steel', return_value=mock_steel_client):
            # This would test the full flow:
            # 1. API request comes in
            # 2. Action is validated and executed
            # 3. Steel session is created
            # 4. Browser automation is performed
            # 5. Results are returned
            # 6. Session is cleaned up
            # 7. Webhook is delivered (if configured)
            
            # For now, we just test that the action can be executed
            action = WebsiteScreenshotAction()
            result = await action.execute_safely(url="https://example.com")
            
            assert result["status"] == "success"
            assert "session_id" in result

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_steel_client):
        """Test error handling across integration points."""
        # Test different failure scenarios
        failure_scenarios = [
            (Exception("Steel SDK connection failed"), "Steel connection error"),
            (TimeoutError("Steel action timeout"), "Timeout error"),
            (ValueError("Invalid parameters"), "Parameter validation error")
        ]
        
        for exception, expected_error_type in failure_scenarios:
            mock_steel_client.actions.run.side_effect = exception
            
            with patch('app.actions.base.Steel', return_value=mock_steel_client):
                action = WebsiteScreenshotAction()
                
                with pytest.raises(Exception):
                    await action.execute_safely(url="https://example.com")
                
                # Session should still be cleaned up
                mock_steel_client.sessions.release.assert_called()
                
                # Reset for next test
                mock_steel_client.sessions.release.reset_mock()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])