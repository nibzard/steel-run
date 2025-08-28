"""Tests for Credential model."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Credential, CredentialType


class TestCredential:
    """Test Credential model."""

    @pytest.mark.asyncio
    async def test_create_credential(self, async_session: AsyncSession, test_user):
        """Test creating a new credential."""
        credential = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Main",
            encrypted_data='{"username": "testuser", "password": "encrypted"}',
        )
        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.id is not None
        assert credential.user_id == test_user.id
        assert credential.service_name == "twitter"
        assert credential.credential_name == "Twitter Main"
        assert credential.encrypted_data == '{"username": "testuser", "password": "encrypted"}'

    @pytest.mark.asyncio
    async def test_credential_defaults(self, async_session: AsyncSession, test_user):
        """Test credential default values."""
        credential = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Main",
            encrypted_data="encrypted_data",
        )
        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.is_active is True

    @pytest.mark.asyncio
    async def test_credential_timestamps(self, async_session: AsyncSession, test_user):
        """Test credential timestamp fields."""
        credential = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Main",
            encrypted_data="encrypted_data",
        )
        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.created_at is not None
        assert credential.updated_at is not None
        assert isinstance(credential.created_at, datetime)
        assert isinstance(credential.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_credential_validation_timestamps(self, async_session: AsyncSession, test_user):
        """Test credential validation timestamp fields."""
        now = datetime.utcnow()
        
        credential = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Main",
            encrypted_data="encrypted_data",
            last_validated=now,
        )
        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        assert credential.last_validated == now

    @pytest.mark.asyncio
    async def test_credential_active_inactive(self, async_session: AsyncSession, test_user):
        """Test credential active/inactive states."""
        # Create active credential
        active_credential = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Active Credential",
            encrypted_data="encrypted_data",
            is_active=True,
        )
        
        # Create inactive credential
        inactive_credential = Credential(
            user_id=test_user.id,
            service_name="linkedin",
            credential_name="Inactive Credential",
            encrypted_data="encrypted_data",
            is_active=False,
        )
        
        async_session.add_all([active_credential, inactive_credential])
        await async_session.commit()
        
        assert active_credential.is_active is True
        assert inactive_credential.is_active is False

    @pytest.mark.asyncio
    async def test_credential_service_names(self, async_session: AsyncSession, test_user):
        """Test credentials with different service names."""
        services = ["twitter", "linkedin", "gmail", "amazon", "custom_service"]
        
        credentials = []
        for service in services:
            credential = Credential(
                user_id=test_user.id,
                service_name=service,
                credential_name=f"{service.title()} Credential",
                encrypted_data="encrypted_data",
            )
            credentials.append(credential)
        
        async_session.add_all(credentials)
        await async_session.commit()
        
        for i, credential in enumerate(credentials):
            await async_session.refresh(credential)
            assert credential.service_name == services[i]

    @pytest.mark.asyncio
    async def test_credential_user_relationship(self, async_session: AsyncSession, test_user):
        """Test credential relationship with user."""
        credential = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Main",
            encrypted_data="encrypted_data",
        )
        async_session.add(credential)
        await async_session.commit()
        await async_session.refresh(credential)

        # Test relationship exists
        assert hasattr(credential, 'user')

    @pytest.mark.asyncio
    async def test_credential_encrypted_data_types(self, async_session: AsyncSession, test_user):
        """Test credentials with different encrypted data formats."""
        # Username/password format
        username_cred = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Username Cred",
            encrypted_data='{"username": "user", "password": "pass"}',
        )
        
        # API key format
        api_key_cred = Credential(
            user_id=test_user.id,
            service_name="api_service",
            credential_name="API Key Cred",
            encrypted_data='{"api_key": "sk_12345"}',
        )
        
        # OAuth token format
        oauth_cred = Credential(
            user_id=test_user.id,
            service_name="oauth_service",
            credential_name="OAuth Cred",
            encrypted_data='{"access_token": "token123", "refresh_token": "refresh123"}',
        )
        
        async_session.add_all([username_cred, api_key_cred, oauth_cred])
        await async_session.commit()
        
        assert "username" in username_cred.encrypted_data
        assert "api_key" in api_key_cred.encrypted_data
        assert "access_token" in oauth_cred.encrypted_data

    @pytest.mark.asyncio
    async def test_credential_uniqueness(self, async_session: AsyncSession, test_user):
        """Test that credentials can be unique per user/service."""
        # Create first credential
        credential1 = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Account 1",
            encrypted_data="encrypted_data_1",
        )
        
        # Create second credential for same service
        credential2 = Credential(
            user_id=test_user.id,
            service_name="twitter",
            credential_name="Twitter Account 2",
            encrypted_data="encrypted_data_2",
        )
        
        async_session.add_all([credential1, credential2])
        await async_session.commit()
        
        assert credential1.credential_name != credential2.credential_name
        assert credential1.encrypted_data != credential2.encrypted_data