"""Tests for authentication endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import APIKey, User
from app.services.auth_service import AuthService


class TestUserRegistration:
    """Test user registration endpoint."""
    
    async def test_register_user_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@steel.run",
            "username": "newuser",
            "full_name": "New User",
            "password": "securepassword123",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert data["is_verified"] is False
    
    async def test_register_user_duplicate_email(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test registration with duplicate email fails."""
        user_data = {
            "email": test_user.email,
            "username": "differentuser",
            "password": "securepassword123",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()
    
    async def test_register_user_duplicate_username(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test registration with duplicate username fails."""
        user_data = {
            "email": "different@steel.run",
            "username": test_user.username,
            "password": "securepassword123",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username already exists" in response.json()["detail"].lower()
    
    @pytest.mark.parametrize("invalid_email", [
        "notanemail",
        "@domain.com",
        "user@",
        "user.domain.com",
        "",
    ])
    async def test_register_user_invalid_email(
        self, async_client: AsyncClient, invalid_email: str
    ):
        """Test registration with invalid email formats fails."""
        user_data = {
            "email": invalid_email,
            "username": "testuser",
            "password": "securepassword123",
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("weak_password", [
        "123",
        "password",
        "12345678",
        "",
    ])
    async def test_register_user_weak_password(
        self, async_client: AsyncClient, weak_password: str
    ):
        """Test registration with weak passwords fails."""
        user_data = {
            "email": "test@steel.run",
            "username": "testuser",
            "password": weak_password,
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login endpoint."""
    
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    async def test_login_wrong_password(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test login with wrong password fails."""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword",
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with nonexistent email fails."""
        login_data = {
            "email": "nonexistent@steel.run",
            "password": "password123",
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_login_inactive_user(
        self, async_client: AsyncClient, inactive_user: User
    ):
        """Test login with inactive user fails."""
        login_data = {
            "email": inactive_user.email,
            "password": "password123",
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in response.json()["detail"].lower()


class TestUserProfile:
    """Test user profile endpoints."""
    
    async def test_get_current_user(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test getting current user profile."""
        response = await async_client.get(
            "/api/v1/auth/me", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["id"] == str(test_user.id)
    
    async def test_get_current_user_unauthorized(self, async_client: AsyncClient):
        """Test getting current user without authentication fails."""
        response = await async_client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_update_user_profile(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test updating user profile."""
        update_data = {
            "full_name": "Updated Full Name",
            "username": "updatedusername",
            "default_region": "nyc",
            "enable_screenshots": False,
        }
        
        response = await async_client.put(
            "/api/v1/auth/me", json=update_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["username"] == update_data["username"]
        assert data["default_region"] == update_data["default_region"]
        assert data["enable_screenshots"] == update_data["enable_screenshots"]
    
    async def test_update_user_profile_duplicate_username(
        self, async_client: AsyncClient, auth_headers: dict, admin_user: User
    ):
        """Test updating profile with duplicate username fails."""
        update_data = {"username": admin_user.username}
        
        response = await async_client.put(
            "/api/v1/auth/me", json=update_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username already exists" in response.json()["detail"].lower()


class TestPasswordChange:
    """Test password change endpoint."""
    
    async def test_change_password_success(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test successful password change."""
        change_data = {
            "current_password": "testpassword123",
            "new_password": "newsecurepassword456",
        }
        
        response = await async_client.post(
            "/api/v1/auth/change-password", json=change_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Password updated successfully"
        
        # Verify login with new password works
        login_data = {
            "email": test_user.email,
            "password": "newsecurepassword456",
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == status.HTTP_200_OK
    
    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test password change with wrong current password fails."""
        change_data = {
            "current_password": "wrongpassword",
            "new_password": "newsecurepassword456",
        }
        
        response = await async_client.post(
            "/api/v1/auth/change-password", json=change_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_change_password_weak_new_password(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test password change with weak new password fails."""
        change_data = {
            "current_password": "testpassword123",
            "new_password": "123",
        }
        
        response = await async_client.post(
            "/api/v1/auth/change-password", json=change_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAPIKeyManagement:
    """Test API key management endpoints."""
    
    async def test_create_api_key(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating a new API key."""
        key_data = {
            "name": "Test Integration Key",
            "rate_limit_per_hour": 1000,
        }
        
        response = await async_client.post(
            "/api/v1/auth/api-keys", json=key_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == key_data["name"]
        assert data["rate_limit_per_hour"] == key_data["rate_limit_per_hour"]
        assert "key" in data  # Raw key should be returned only on creation
        assert data["key"].startswith("sk_")
        assert "key_prefix" in data
        assert data["is_active"] is True
    
    async def test_list_api_keys(
        self, async_client: AsyncClient, auth_headers: dict, test_api_key: APIKey
    ):
        """Test listing user's API keys."""
        response = await async_client.get(
            "/api/v1/auth/api-keys", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our test key
        test_key_data = next(
            (key for key in data if key["name"] == test_api_key.name), None
        )
        assert test_key_data is not None
        assert test_key_data["key_prefix"] == test_api_key.key_prefix
        assert "key" not in test_key_data  # Raw key should not be in list
    
    async def test_get_api_key(
        self, async_client: AsyncClient, auth_headers: dict, test_api_key: APIKey
    ):
        """Test getting specific API key."""
        response = await async_client.get(
            f"/api/v1/auth/api-keys/{test_api_key.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_api_key.id)
        assert data["name"] == test_api_key.name
        assert data["key_prefix"] == test_api_key.key_prefix
        assert "key" not in data  # Raw key should not be returned
    
    async def test_update_api_key(
        self, async_client: AsyncClient, auth_headers: dict, test_api_key: APIKey
    ):
        """Test updating API key."""
        update_data = {
            "name": "Updated Key Name",
            "rate_limit_per_hour": 200,
            "is_active": False,
        }
        
        response = await async_client.put(
            f"/api/v1/auth/api-keys/{test_api_key.id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["rate_limit_per_hour"] == update_data["rate_limit_per_hour"]
        assert data["is_active"] == update_data["is_active"]
    
    async def test_delete_api_key(
        self, async_client: AsyncClient, auth_headers: dict, test_api_key: APIKey
    ):
        """Test deleting API key."""
        response = await async_client.delete(
            f"/api/v1/auth/api-keys/{test_api_key.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify key is deleted
        get_response = await async_client.get(
            f"/api/v1/auth/api-keys/{test_api_key.id}", headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_api_key_access_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict, test_api_key: APIKey
    ):
        """Test that users can't access other users' API keys."""
        response = await async_client.get(
            f"/api/v1/auth/api-keys/{test_api_key.id}", headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAPIKeyAuthentication:
    """Test API key authentication."""
    
    async def test_api_key_authentication_success(
        self, async_client: AsyncClient, api_key_headers: dict
    ):
        """Test successful API key authentication."""
        response = await async_client.get(
            "/api/v1/auth/me", headers=api_key_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email" in data
    
    async def test_api_key_authentication_invalid_key(self, async_client: AsyncClient):
        """Test API key authentication with invalid key."""
        headers = {"X-API-Key": "invalid_key"}
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_api_key_authentication_expired_key(
        self, async_client: AsyncClient, expired_api_key: APIKey
    ):
        """Test API key authentication with expired key."""
        headers = {"X-API-Key": expired_api_key._raw_key}  # type: ignore
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in response.json()["detail"].lower()
    
    async def test_api_key_rate_limiting(
        self, async_client: AsyncClient, api_key_headers: dict, test_api_key: APIKey
    ):
        """Test API key rate limiting."""
        # This would require mocking the rate limiter
        # or setting up a test scenario with very low limits
        # For now, just test that the endpoint responds normally
        response = await async_client.get(
            "/api/v1/auth/me", headers=api_key_headers
        )
        
        assert response.status_code == status.HTTP_200_OK


class TestTokenAuthentication:
    """Test JWT token authentication."""
    
    async def test_token_authentication_success(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test successful token authentication."""
        response = await async_client.get(
            "/api/v1/auth/me", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    async def test_token_authentication_invalid_token(self, async_client: AsyncClient):
        """Test token authentication with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_token_authentication_malformed_header(self, async_client: AsyncClient):
        """Test token authentication with malformed header."""
        headers = {"Authorization": "Invalid token_format"}
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_token_authentication_missing_header(self, async_client: AsyncClient):
        """Test protected endpoint without authentication header."""
        response = await async_client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
class TestSecurityHeaders:
    """Test security-related features in auth endpoints."""
    
    async def test_password_not_returned(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that password/hash is never returned in responses."""
        response = await async_client.get(
            "/api/v1/auth/me", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password" not in data
        assert "hashed_password" not in data
    
    async def test_login_response_security(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test that login response doesn't leak sensitive data."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123",
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "password" not in data
        assert "hashed_password" not in data
        assert "access_token" in data
        assert "token_type" in data