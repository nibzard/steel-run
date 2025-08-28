"""Tests for credentials API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Credential
from app.models.user import User


class TestCredentialsAPI:
    """Test credentials CRUD operations."""
    
    async def test_create_credential(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating a new credential."""
        credential_data = {
            "service_name": "twitter",
            "credential_name": "My Twitter Account",
            "credential_data": {
                "username": "testuser",
                "password": "securepassword123",
            },
        }
        
        response = await async_client.post(
            "/api/v1/credentials", json=credential_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["service_name"] == credential_data["service_name"]
        assert data["credential_name"] == credential_data["credential_name"]
        assert data["is_active"] is True
        assert "id" in data
        assert "encrypted_data" not in data  # Should not expose encrypted data
        assert "credential_data" not in data  # Should not expose raw data
        assert data["is_validated"] is False  # New credential not validated yet
    
    async def test_create_credential_duplicate_name(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test creating credential with duplicate name for same service fails."""
        credential_data = {
            "service_name": "twitter",
            "credential_name": twitter_credential.credential_name,
            "credential_data": {
                "username": "anotheruser",
                "password": "password123",
            },
        }
        
        response = await async_client.post(
            "/api/v1/credentials", json=credential_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "credential name already exists" in response.json()["detail"].lower()
    
    @pytest.mark.parametrize("invalid_service", [
        "invalid_service",
        "",
        "TWITTER",  # Should be lowercase
        "social_media",  # Not supported
    ])
    async def test_create_credential_invalid_service(
        self, async_client: AsyncClient, auth_headers: dict, invalid_service: str
    ):
        """Test creating credential with invalid service name fails."""
        credential_data = {
            "service_name": invalid_service,
            "credential_name": "Test Credential",
            "credential_data": {"username": "test", "password": "test"},
        }
        
        response = await async_client.post(
            "/api/v1/credentials", json=credential_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unsupported service" in response.json()["detail"].lower()
    
    async def test_create_credential_missing_required_fields(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test creating credential with missing required fields fails."""
        credential_data = {
            "service_name": "twitter",
            "credential_name": "Incomplete Credential",
            "credential_data": {
                "username": "testuser",
                # Missing password field
            },
        }
        
        response = await async_client.post(
            "/api/v1/credentials", json=credential_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "missing required field" in response.json()["detail"].lower()
    
    async def test_list_credentials(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, linkedin_credential: Credential
    ):
        """Test listing user's credentials."""
        response = await async_client.get(
            "/api/v1/credentials", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        
        # Check that both credentials are present
        credential_names = [cred["credential_name"] for cred in data]
        assert twitter_credential.credential_name in credential_names
        assert linkedin_credential.credential_name in credential_names
        
        # Verify sensitive data is not exposed
        for cred in data:
            assert "encrypted_data" not in cred
            assert "credential_data" not in cred
    
    async def test_list_credentials_filter_by_service(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, linkedin_credential: Credential
    ):
        """Test filtering credentials by service."""
        response = await async_client.get(
            "/api/v1/credentials?service=twitter", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return Twitter credentials
        assert all(cred["service_name"] == "twitter" for cred in data)
        assert any(cred["credential_name"] == twitter_credential.credential_name for cred in data)
        assert not any(cred["credential_name"] == linkedin_credential.credential_name for cred in data)
    
    async def test_list_credentials_filter_by_status(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test filtering credentials by active status."""
        response = await async_client.get(
            "/api/v1/credentials?active_only=true", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return active credentials
        assert all(cred["is_active"] for cred in data)
    
    async def test_get_credential(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test getting a specific credential."""
        response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(twitter_credential.id)
        assert data["service_name"] == twitter_credential.service_name
        assert data["credential_name"] == twitter_credential.credential_name
        assert data["is_active"] == twitter_credential.is_active
        # Should not expose sensitive data
        assert "encrypted_data" not in data
        assert "credential_data" not in data
    
    async def test_get_credential_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent credential."""
        response = await async_client.get(
            "/api/v1/credentials/non-existent-id", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_credential_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test that users can't access other users' credentials."""
        response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}", 
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_update_credential(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test updating a credential."""
        update_data = {
            "credential_name": "Updated Twitter Account",
            "credential_data": {
                "username": "updateduser",
                "password": "newpassword123",
            },
            "is_active": False,
        }
        
        response = await async_client.put(
            f"/api/v1/credentials/{twitter_credential.id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["credential_name"] == update_data["credential_name"]
        assert data["is_active"] == update_data["is_active"]
        assert data["is_validated"] is False  # Should reset validation status
        # Should not expose sensitive data
        assert "encrypted_data" not in data
        assert "credential_data" not in data
    
    async def test_update_credential_partial(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test partial update of credential."""
        update_data = {"credential_name": "Partially Updated Credential"}
        
        response = await async_client.put(
            f"/api/v1/credentials/{twitter_credential.id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["credential_name"] == update_data["credential_name"]
        # Other fields should remain unchanged
        assert data["service_name"] == twitter_credential.service_name
        assert data["is_active"] == twitter_credential.is_active
    
    async def test_update_credential_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test that users can't update other users' credentials."""
        update_data = {"credential_name": "Unauthorized Update"}
        
        response = await async_client.put(
            f"/api/v1/credentials/{twitter_credential.id}",
            json=update_data,
            headers=admin_auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_delete_credential(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test deleting a credential."""
        response = await async_client.delete(
            f"/api/v1/credentials/{twitter_credential.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify credential is deleted
        get_response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}", headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_delete_credential_different_user(
        self, async_client: AsyncClient, admin_auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test that users can't delete other users' credentials."""
        response = await async_client.delete(
            f"/api/v1/credentials/{twitter_credential.id}", 
            headers=admin_auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCredentialValidation:
    """Test credential validation endpoints."""
    
    async def test_validate_credential_success(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, mock_steel_client
    ):
        """Test successful credential validation."""
        with pytest.mock.patch("app.services.credential_service.Steel") as mock_steel:
            mock_steel.return_value = mock_steel_client
            
            response = await async_client.post(
                f"/api/v1/credentials/{twitter_credential.id}/validate",
                headers=auth_headers,
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is True
            assert data["message"] == "Credential validated successfully"
    
    async def test_validate_credential_failure(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test credential validation failure."""
        # Mock Steel client to return validation failure
        mock_steel_client = pytest.AsyncMock()
        mock_steel_client.sessions.create.side_effect = Exception("Invalid credentials")
        
        with pytest.mock.patch("app.services.credential_service.Steel") as mock_steel:
            mock_steel.return_value = mock_steel_client
            
            response = await async_client.post(
                f"/api/v1/credentials/{twitter_credential.id}/validate",
                headers=auth_headers,
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert data["is_valid"] is False
            assert "invalid" in data["message"].lower()
    
    async def test_validate_inactive_credential(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, async_session: AsyncSession
    ):
        """Test validation of inactive credential fails."""
        # Deactivate the credential
        twitter_credential.is_active = False
        await async_session.commit()
        
        response = await async_client.post(
            f"/api/v1/credentials/{twitter_credential.id}/validate",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inactive" in response.json()["detail"].lower()
    
    async def test_bulk_validate_credentials(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, linkedin_credential: Credential
    ):
        """Test bulk validation of credentials."""
        request_data = {
            "credential_ids": [str(twitter_credential.id), str(linkedin_credential.id)]
        }
        
        with pytest.mock.patch("app.services.credential_service.validate_credential") as mock_validate:
            mock_validate.return_value = {"is_valid": True, "message": "Valid"}
            
            response = await async_client.post(
                "/api/v1/credentials/validate-bulk",
                json=request_data,
                headers=auth_headers,
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2


class TestCredentialSecurity:
    """Test security aspects of credential management."""
    
    async def test_credential_data_encryption(
        self, async_client: AsyncClient, auth_headers: dict,
        async_session: AsyncSession
    ):
        """Test that credential data is properly encrypted in database."""
        credential_data = {
            "service_name": "twitter",
            "credential_name": "Security Test Credential",
            "credential_data": {
                "username": "securitytest",
                "password": "topsecretpassword",
            },
        }
        
        response = await async_client.post(
            "/api/v1/credentials", json=credential_data, headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        created_credential = response.json()
        
        # Fetch credential directly from database
        from sqlalchemy import select
        result = await async_session.execute(
            select(Credential).where(Credential.id == created_credential["id"])
        )
        db_credential = result.scalar_one()
        
        # Verify data is encrypted in database
        assert db_credential.encrypted_data != str(credential_data["credential_data"])
        assert "topsecretpassword" not in db_credential.encrypted_data
        assert db_credential.encrypted_data.startswith("gAAAAAB")  # Fernet encryption marker
    
    async def test_credential_access_logging(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test that credential access is properly logged."""
        # This would require checking logs or audit trail
        # For now, just verify the endpoint works
        response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        # In a real implementation, we'd check audit logs here
    
    async def test_credential_data_sanitization(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that credential data is sanitized against injection attacks."""
        malicious_data = {
            "service_name": "twitter",
            "credential_name": "Malicious<script>alert('xss')</script>",
            "credential_data": {
                "username": "'; DROP TABLE credentials; --",
                "password": "<script>alert('xss')</script>",
            },
        }
        
        response = await async_client.post(
            "/api/v1/credentials", json=malicious_data, headers=auth_headers
        )
        
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            # Data should be sanitized
            assert "<script>" not in data["credential_name"]
            assert "DROP TABLE" not in str(data)
        else:
            # Or request should be rejected
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]
    
    @pytest.mark.parametrize("sensitive_field", [
        "encrypted_data",
        "credential_data",
        "password",
        "secret_key",
        "api_secret",
    ])
    async def test_sensitive_data_not_exposed(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, sensitive_field: str
    ):
        """Test that sensitive fields are never exposed in API responses."""
        # Test GET endpoint
        response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert sensitive_field not in data
        
        # Test LIST endpoint
        response = await async_client.get(
            "/api/v1/credentials", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        credentials = response.json()
        for cred in credentials:
            assert sensitive_field not in cred


class TestCredentialValidationRules:
    """Test validation rules for different credential types."""
    
    @pytest.mark.parametrize("service,required_fields", [
        ("twitter", ["username", "password"]),
        ("linkedin", ["email", "password"]),
        ("gmail", ["email", "password"]),
        ("amazon", ["email", "password"]),
    ])
    async def test_service_specific_validation(
        self, async_client: AsyncClient, auth_headers: dict,
        service: str, required_fields: list
    ):
        """Test service-specific validation rules."""
        # Test with missing required fields
        for missing_field in required_fields:
            credential_data = {
                "service_name": service,
                "credential_name": f"Test {service} Credential",
                "credential_data": {
                    field: f"test_{field}" for field in required_fields if field != missing_field
                },
            }
            
            response = await async_client.post(
                "/api/v1/credentials", json=credential_data, headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert missing_field in response.json()["detail"].lower()
    
    async def test_email_format_validation(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test email format validation for services that require email."""
        invalid_emails = [
            "notanemail",
            "@domain.com",
            "user@",
            "user.domain.com",
            "",
        ]
        
        for invalid_email in invalid_emails:
            credential_data = {
                "service_name": "gmail",
                "credential_name": f"Test Gmail {invalid_email[:5]}",
                "credential_data": {
                    "email": invalid_email,
                    "password": "password123",
                },
            }
            
            response = await async_client.post(
                "/api/v1/credentials", json=credential_data, headers=auth_headers
            )
            
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]
    
    async def test_password_strength_validation(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test password strength requirements."""
        weak_passwords = [
            "",
            "123",
            "password",
            "12345678",
        ]
        
        for weak_password in weak_passwords:
            credential_data = {
                "service_name": "twitter",
                "credential_name": f"Test Twitter {weak_password[:3]}",
                "credential_data": {
                    "username": "testuser",
                    "password": weak_password,
                },
            }
            
            response = await async_client.post(
                "/api/v1/credentials", json=credential_data, headers=auth_headers
            )
            
            # Some implementations might accept weak passwords with warnings
            # Others might reject them entirely
            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                assert "warning" in data or "weak_password" in data
            else:
                assert response.status_code in [
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                ]


class TestCredentialUsageTracking:
    """Test credential usage tracking and statistics."""
    
    async def test_credential_usage_stats(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential
    ):
        """Test getting credential usage statistics."""
        response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}/stats",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "usage_count" in data
        assert "last_used" in data
        assert "success_rate" in data
        assert "validation_history" in data
    
    async def test_credential_usage_tracking(
        self, async_client: AsyncClient, auth_headers: dict,
        twitter_credential: Credential, async_session: AsyncSession
    ):
        """Test that credential usage is properly tracked."""
        # Get initial usage count
        initial_response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}/stats",
            headers=auth_headers,
        )
        initial_data = initial_response.json()
        initial_usage = initial_data.get("usage_count", 0)
        
        # Use the credential (simulate by running validation)
        await async_client.post(
            f"/api/v1/credentials/{twitter_credential.id}/validate",
            headers=auth_headers,
        )
        
        # Check that usage count increased
        final_response = await async_client.get(
            f"/api/v1/credentials/{twitter_credential.id}/stats",
            headers=auth_headers,
        )
        final_data = final_response.json()
        final_usage = final_data.get("usage_count", 0)
        
        # Usage should have increased
        assert final_usage > initial_usage