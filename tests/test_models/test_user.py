"""Tests for User model."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, APIKey
from app.utils.auth import hash_api_key


class TestUser:
    """Test User model."""

    @pytest.mark.asyncio
    async def test_create_user(self, async_session: AsyncSession):
        """Test creating a new user."""
        user = User(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password="hashed_password",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.total_actions_run == 0

    @pytest.mark.asyncio
    async def test_user_relationships(self, async_session: AsyncSession):
        """Test user relationships with other models."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Test that relationship attributes exist
        assert hasattr(user, 'api_keys')
        assert hasattr(user, 'stored_actions')
        assert hasattr(user, 'credentials')
        assert hasattr(user, 'execution_runs')

    @pytest.mark.asyncio
    async def test_user_defaults(self, async_session: AsyncSession):
        """Test user default values."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.is_active is True
        assert user.is_verified is False
        assert user.total_actions_run == 0
        assert user.default_region == "lax"
        assert user.enable_screenshots is True
        assert user.enable_webhooks is True

    @pytest.mark.asyncio
    async def test_user_timestamps(self, async_session: AsyncSession):
        """Test user timestamp fields."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)


class TestAPIKey:
    """Test APIKey model."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, async_session: AsyncSession, test_user: User):
        """Test creating a new API key."""
        raw_key = "sk_test_1234567890"
        key_hash = hash_api_key(raw_key)
        
        api_key = APIKey(
            user_id=test_user.id,
            name="Test API Key",
            key_hash=key_hash,
            key_prefix="sk_test_123",
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        assert api_key.id is not None
        assert api_key.user_id == test_user.id
        assert api_key.name == "Test API Key"
        assert api_key.key_hash == key_hash
        assert api_key.key_prefix == "sk_test_123"
        assert api_key.is_active is True

    @pytest.mark.asyncio
    async def test_api_key_defaults(self, async_session: AsyncSession, test_user: User):
        """Test API key default values."""
        api_key = APIKey(
            user_id=test_user.id,
            name="Test API Key",
            key_hash="test_hash",
            key_prefix="sk_test",
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        assert api_key.is_active is True
        assert api_key.rate_limit_per_hour == 500
        assert api_key.usage_count == 0

    @pytest.mark.asyncio
    async def test_api_key_expiration(self, async_session: AsyncSession, test_user: User):
        """Test API key expiration."""
        past_date = datetime.utcnow() - timedelta(days=1)
        future_date = datetime.utcnow() + timedelta(days=30)
        
        expired_key = APIKey(
            user_id=test_user.id,
            name="Expired Key",
            key_hash="expired_hash",
            key_prefix="sk_exp",
            expires_at=past_date,
        )
        
        valid_key = APIKey(
            user_id=test_user.id,
            name="Valid Key",
            key_hash="valid_hash",
            key_prefix="sk_val",
            expires_at=future_date,
        )
        
        async_session.add_all([expired_key, valid_key])
        await async_session.commit()
        
        assert expired_key.expires_at == past_date
        assert valid_key.expires_at == future_date

    @pytest.mark.asyncio
    async def test_api_key_usage_tracking(self, async_session: AsyncSession, test_user: User):
        """Test API key usage tracking."""
        api_key = APIKey(
            user_id=test_user.id,
            name="Test API Key",
            key_hash="test_hash",
            key_prefix="sk_test",
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        # Update usage
        api_key.usage_count = 10
        api_key.last_used = datetime.utcnow()
        await async_session.commit()
        await async_session.refresh(api_key)

        assert api_key.usage_count == 10
        assert api_key.last_used is not None

    @pytest.mark.asyncio
    async def test_api_key_user_relationship(self, async_session: AsyncSession, test_user: User):
        """Test API key relationship with user."""
        api_key = APIKey(
            user_id=test_user.id,
            name="Test API Key",
            key_hash="test_hash",
            key_prefix="sk_test",
        )
        async_session.add(api_key)
        await async_session.commit()
        await async_session.refresh(api_key)

        # Test back-reference
        await async_session.refresh(test_user)
        assert hasattr(api_key, 'user')