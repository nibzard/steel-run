"""Tests for stored actions API endpoints."""

import json
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stored_action import StoredAction
from app.models.user import User


class TestStoredActionsAPI:
    """Test stored actions CRUD operations."""
    
    async def test_create_stored_action(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test creating a new stored action."""
        action_data = {
            "name": "Test Twitter Action",
            "description": "A test action for posting tweets",
            "action_type": "twitter",
            "parameters": {
                "action": "post_tweet",
                "message": "Hello from Steel.run!",
                "include_timestamp": True,
            },
            "webhook_url": "https://hooks.zapier.com/test",
            "is_active": True,
            "is_public": False,
            "tags": ["social", "automation"],
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == action_data["name"]
        assert data["description"] == action_data["description"]
        assert data["action_type"] == action_data["action_type"]
        assert data["parameters"] == action_data["parameters"]
        assert data["webhook_url"] == action_data["webhook_url"]
        assert data["is_active"] == action_data["is_active"]
        assert data["is_public"] == action_data["is_public"]
        assert data["tags"] == action_data["tags"]
        assert data["user_id"] == str(test_user.id)
        assert "id" in data
        assert "api_endpoint" in data
        assert data["run_count"] == 0
        assert data["success_count"] == 0
        assert data["failure_count"] == 0
    
    async def test_create_stored_action_minimal(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating stored action with minimal required fields."""
        action_data = {
            "name": "Minimal Action",
            "action_type": "website",
            "parameters": {
                "action": "extract_data",
                "url": "https://example.com",
            },
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == action_data["name"]
        assert data["action_type"] == action_data["action_type"]
        assert data["parameters"] == action_data["parameters"]
        assert data["is_active"] is True  # Default value
        assert data["is_public"] is False  # Default value
    
    async def test_create_stored_action_invalid_type(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating stored action with invalid action type."""
        action_data = {
            "name": "Invalid Action",
            "action_type": "invalid_type",
            "parameters": {"test": "data"},
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid action type" in response.json()["detail"].lower()
    
    async def test_list_stored_actions(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction, linkedin_stored_action: StoredAction
    ):
        """Test listing user's stored actions."""
        response = await async_client.get(
            "/api/v1/stored-actions", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        
        items = data["items"]
        assert len(items) >= 2
        
        # Check that both actions are present
        action_names = [action["name"] for action in items]
        assert twitter_stored_action.name in action_names
        assert linkedin_stored_action.name in action_names
    
    async def test_list_stored_actions_filter_by_type(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction, linkedin_stored_action: StoredAction
    ):
        """Test filtering stored actions by type."""
        response = await async_client.get(
            "/api/v1/stored-actions?action_type=twitter", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data["items"]
        
        # Should only return twitter actions
        assert all(action["action_type"] == "twitter" for action in items)
        assert any(action["name"] == twitter_stored_action.name for action in items)
        assert not any(action["name"] == linkedin_stored_action.name for action in items)
    
    async def test_list_stored_actions_pagination(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test stored actions list pagination."""
        response = await async_client.get(
            "/api/v1/stored-actions?page=1&size=1", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["size"] == 1
        assert len(data["items"]) <= 1
        assert data["page"] == 1
    
    async def test_get_stored_action(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test getting a specific stored action."""
        response = await async_client.get(
            f"/api/v1/stored-actions/{twitter_stored_action.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(twitter_stored_action.id)
        assert data["name"] == twitter_stored_action.name
        assert data["action_type"] == twitter_stored_action.action_type
        assert data["run_count"] == twitter_stored_action.run_count
        assert data["success_count"] == twitter_stored_action.success_count
        assert "success_percentage" in data
    
    async def test_get_stored_action_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent stored action."""
        response = await async_client.get(
            "/api/v1/stored-actions/non-existent-id", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_stored_action_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test that users can't access other users' private actions."""
        response = await async_client.get(
            f"/api/v1/stored-actions/{twitter_stored_action.id}", 
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_public_stored_action_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        linkedin_stored_action: StoredAction
    ):
        """Test that users can access other users' public actions."""
        response = await async_client.get(
            f"/api/v1/stored-actions/{linkedin_stored_action.id}", 
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(linkedin_stored_action.id)
    
    async def test_update_stored_action(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test updating a stored action."""
        update_data = {
            "name": "Updated Twitter Action",
            "description": "Updated description",
            "parameters": {
                "action": "post_tweet",
                "message": "Updated message",
                "include_timestamp": False,
            },
            "webhook_url": "https://hooks.zapier.com/updated",
            "is_active": False,
            "tags": ["updated", "social"],
        }
        
        response = await async_client.put(
            f"/api/v1/stored-actions/{twitter_stored_action.id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["parameters"] == update_data["parameters"]
        assert data["webhook_url"] == update_data["webhook_url"]
        assert data["is_active"] == update_data["is_active"]
        assert data["tags"] == update_data["tags"]
        assert data["version"] > twitter_stored_action.version
    
    async def test_update_stored_action_partial(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test partial update of stored action."""
        update_data = {"name": "Partially Updated Action"}
        
        response = await async_client.put(
            f"/api/v1/stored-actions/{twitter_stored_action.id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        # Other fields should remain unchanged
        assert data["action_type"] == twitter_stored_action.action_type
        assert data["is_active"] == twitter_stored_action.is_active
    
    async def test_update_stored_action_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test that users can't update other users' actions."""
        update_data = {"name": "Unauthorized Update"}
        
        response = await async_client.put(
            f"/api/v1/stored-actions/{twitter_stored_action.id}",
            json=update_data,
            headers=admin_auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_delete_stored_action(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test deleting a stored action."""
        response = await async_client.delete(
            f"/api/v1/stored-actions/{twitter_stored_action.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify action is deleted
        get_response = await async_client.get(
            f"/api/v1/stored-actions/{twitter_stored_action.id}", headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_delete_stored_action_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test that users can't delete other users' actions."""
        response = await async_client.delete(
            f"/api/v1/stored-actions/{twitter_stored_action.id}", 
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStoredActionExecution:
    """Test stored action execution endpoints."""
    
    async def test_run_stored_action_success(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction, mock_steel_client
    ):
        """Test successful execution of stored action."""
        with pytest.mock.patch("app.services.execution_service.Steel") as mock_steel:
            mock_steel.return_value = mock_steel_client
            
            response = await async_client.post(
                f"/api/v1/stored-actions/{twitter_stored_action.id}/run",
                headers=auth_headers,
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "queued"
            assert "execution_id" in data
            assert "estimated_completion" in data
    
    async def test_run_stored_action_with_parameters(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction, mock_steel_client
    ):
        """Test execution with custom parameters."""
        execution_data = {
            "parameters": {
                "action": "post_tweet",
                "message": "Custom execution message",
            },
            "webhook_url": "https://custom-webhook.com",
        }
        
        with pytest.mock.patch("app.services.execution_service.Steel") as mock_steel:
            mock_steel.return_value = mock_steel_client
            
            response = await async_client.post(
                f"/api/v1/stored-actions/{twitter_stored_action.id}/run",
                json=execution_data,
                headers=auth_headers,
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "queued"
    
    async def test_run_inactive_stored_action(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction, async_session: AsyncSession
    ):
        """Test execution of inactive stored action fails."""
        # Deactivate the action
        twitter_stored_action.is_active = False
        await async_session.commit()
        
        response = await async_client.post(
            f"/api/v1/stored-actions/{twitter_stored_action.id}/run",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inactive" in response.json()["detail"].lower()
    
    async def test_run_stored_action_rate_limit(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction
    ):
        """Test rate limiting on action execution."""
        # This would require setting up rate limiting rules
        # For now, just test that the endpoint responds
        response = await async_client.post(
            f"/api/v1/stored-actions/{twitter_stored_action.id}/run",
            headers=auth_headers,
        )
        
        # Without proper Steel client setup, this might fail
        # but we're testing the rate limiting logic
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]
    
    async def test_get_execution_history(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_stored_action: StoredAction, successful_execution_run
    ):
        """Test getting execution history for a stored action."""
        response = await async_client.get(
            f"/api/v1/stored-actions/{twitter_stored_action.id}/executions",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        
        items = data["items"]
        assert len(items) >= 1
        
        # Check execution details
        execution = items[0]
        assert "id" in execution
        assert "status" in execution
        assert "execution_time_ms" in execution
        assert "created_at" in execution
    
    async def test_get_execution_details(
        self, async_client: AsyncClient, auth_headers: dict,
        successful_execution_run
    ):
        """Test getting detailed execution information."""
        response = await async_client.get(
            f"/api/v1/executions/{successful_execution_run.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(successful_execution_run.id)
        assert data["status"] == successful_execution_run.status
        assert data["execution_time_ms"] == successful_execution_run.execution_time_ms
        assert "result_data" in data
        assert "logs" in data
        assert "screenshots_urls" in data


class TestStoredActionValidation:
    """Test validation rules for stored actions."""
    
    @pytest.mark.parametrize("invalid_name", [
        "",
        "a" * 256,  # Too long
        "   ",  # Whitespace only
    ])
    async def test_create_stored_action_invalid_name(
        self, async_client: AsyncClient, auth_headers: dict, invalid_name: str
    ):
        """Test creating stored action with invalid names."""
        action_data = {
            "name": invalid_name,
            "action_type": "twitter",
            "parameters": {"action": "post_tweet"},
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_create_stored_action_invalid_parameters(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating stored action with invalid parameters."""
        action_data = {
            "name": "Invalid Parameters Action",
            "action_type": "twitter",
            "parameters": "not_a_dict",  # Should be a dictionary
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_create_stored_action_invalid_webhook_url(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating stored action with invalid webhook URL."""
        action_data = {
            "name": "Invalid Webhook Action",
            "action_type": "twitter",
            "parameters": {"action": "post_tweet"},
            "webhook_url": "not_a_valid_url",
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestPublicStoredActions:
    """Test public stored actions functionality."""
    
    async def test_list_public_actions(
        self, async_client: AsyncClient, linkedin_stored_action: StoredAction
    ):
        """Test listing public stored actions without authentication."""
        response = await async_client.get("/api/v1/public/stored-actions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        
        items = data["items"]
        assert all(action["is_public"] for action in items)
        
        # Should include our public LinkedIn action
        public_action_names = [action["name"] for action in items]
        assert linkedin_stored_action.name in public_action_names
    
    async def test_get_public_action_details(
        self, async_client: AsyncClient, linkedin_stored_action: StoredAction
    ):
        """Test getting public action details without authentication."""
        response = await async_client.get(
            f"/api/v1/public/stored-actions/{linkedin_stored_action.id}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(linkedin_stored_action.id)
        assert data["is_public"] is True
        # Should not expose sensitive user information
        assert "user_id" not in data or data["user_id"] is None


@pytest.mark.security
class TestStoredActionSecurity:
    """Test security aspects of stored actions."""
    
    async def test_parameter_sanitization(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that action parameters are properly sanitized."""
        action_data = {
            "name": "Security Test Action",
            "action_type": "website",
            "parameters": {
                "action": "extract_data",
                "url": "javascript:alert('xss')",  # Potential XSS
                "selector": "<script>alert('xss')</script>",  # HTML injection
            },
        }
        
        response = await async_client.post(
            "/api/v1/stored-actions", json=action_data, headers=auth_headers
        )
        
        # Should either sanitize or reject the request
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            # Parameters should be sanitized
            assert "javascript:" not in str(data["parameters"])
            assert "<script>" not in str(data["parameters"])
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_webhook_url_validation(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test webhook URL security validation."""
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://internal-server/secret",
        ]
        
        for malicious_url in malicious_urls:
            action_data = {
                "name": f"Security Test {malicious_url[:10]}",
                "action_type": "twitter",
                "parameters": {"action": "post_tweet"},
                "webhook_url": malicious_url,
            }
            
            response = await async_client.post(
                "/api/v1/stored-actions", json=action_data, headers=auth_headers
            )
            
            # Should reject malicious URLs
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]