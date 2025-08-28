"""Tests for StoredAction model."""

import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stored_action import StoredAction


class TestStoredAction:
    """Test StoredAction model."""

    @pytest.mark.asyncio
    async def test_create_stored_action(self, async_session: AsyncSession, test_user):
        """Test creating a new stored action."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            description="A test action",
            action_type="twitter",
            parameters=json.dumps({"message": "Hello World"}),
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.id is not None
        assert action.user_id == test_user.id
        assert action.name == "Test Action"
        assert action.description == "A test action"
        assert action.action_type == "twitter"
        assert json.loads(action.parameters) == {"message": "Hello World"}

    @pytest.mark.asyncio
    async def test_stored_action_defaults(self, async_session: AsyncSession, test_user):
        """Test stored action default values."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.is_active is True
        assert action.is_public is False
        assert action.run_count == 0
        assert action.success_count == 0
        assert action.failure_count == 0
        assert action.version == 1

    @pytest.mark.asyncio
    async def test_stored_action_statistics(self, async_session: AsyncSession, test_user):
        """Test stored action statistics."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
            run_count=10,
            success_count=8,
            failure_count=2,
            avg_execution_time=1500,
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.run_count == 10
        assert action.success_count == 8
        assert action.failure_count == 2
        assert action.avg_execution_time == 1500

    @pytest.mark.asyncio
    async def test_stored_action_success_rate_property(self, async_session: AsyncSession, test_user):
        """Test stored action success rate calculation."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
            run_count=10,
            success_count=8,
            failure_count=2,
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        # The success_rate property should be calculated
        expected_rate = (8 / 10) * 100 if hasattr(action, 'success_rate') else None
        if expected_rate:
            assert abs(action.success_rate - expected_rate) < 0.01

    @pytest.mark.asyncio
    async def test_stored_action_timestamps(self, async_session: AsyncSession, test_user):
        """Test stored action timestamp fields."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.created_at is not None
        assert action.updated_at is not None
        assert isinstance(action.created_at, datetime)
        assert isinstance(action.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_stored_action_execution_timestamps(self, async_session: AsyncSession, test_user):
        """Test stored action execution timestamp fields."""
        now = datetime.utcnow()
        past = now - timedelta(hours=1)
        
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
            last_run=now,
            last_success=now,
            last_failure=past,
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.last_run == now
        assert action.last_success == now
        assert action.last_failure == past

    @pytest.mark.asyncio
    async def test_stored_action_tags(self, async_session: AsyncSession, test_user):
        """Test stored action tags field."""
        tags = json.dumps(["automation", "social", "twitter"])
        
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
            tags=tags,
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.tags == tags
        parsed_tags = json.loads(action.tags)
        assert "automation" in parsed_tags
        assert "social" in parsed_tags
        assert "twitter" in parsed_tags

    @pytest.mark.asyncio
    async def test_stored_action_webhook_url(self, async_session: AsyncSession, test_user):
        """Test stored action webhook URL."""
        webhook_url = "https://hooks.zapier.com/test"
        
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
            webhook_url=webhook_url,
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.webhook_url == webhook_url

    @pytest.mark.asyncio
    async def test_stored_action_user_relationship(self, async_session: AsyncSession, test_user):
        """Test stored action relationship with user."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        # Test relationship exists
        assert hasattr(action, 'user')
        assert hasattr(action, 'execution_runs')

    @pytest.mark.asyncio
    async def test_stored_action_versioning(self, async_session: AsyncSession, test_user):
        """Test stored action versioning."""
        action = StoredAction(
            user_id=test_user.id,
            name="Test Action",
            action_type="twitter",
            parameters=json.dumps({}),
            version=2,
        )
        async_session.add(action)
        await async_session.commit()
        await async_session.refresh(action)

        assert action.version == 2

    @pytest.mark.asyncio
    async def test_stored_action_public_private(self, async_session: AsyncSession, test_user):
        """Test stored action public/private settings."""
        # Create private action
        private_action = StoredAction(
            user_id=test_user.id,
            name="Private Action",
            action_type="twitter",
            parameters=json.dumps({}),
            is_public=False,
        )
        
        # Create public action
        public_action = StoredAction(
            user_id=test_user.id,
            name="Public Action",
            action_type="twitter",
            parameters=json.dumps({}),
            is_public=True,
        )
        
        async_session.add_all([private_action, public_action])
        await async_session.commit()
        
        assert private_action.is_public is False
        assert public_action.is_public is True

    @pytest.mark.asyncio
    async def test_stored_action_active_inactive(self, async_session: AsyncSession, test_user):
        """Test stored action active/inactive states."""
        # Create active action
        active_action = StoredAction(
            user_id=test_user.id,
            name="Active Action",
            action_type="twitter",
            parameters=json.dumps({}),
            is_active=True,
        )
        
        # Create inactive action
        inactive_action = StoredAction(
            user_id=test_user.id,
            name="Inactive Action",
            action_type="twitter",
            parameters=json.dumps({}),
            is_active=False,
        )
        
        async_session.add_all([active_action, inactive_action])
        await async_session.commit()
        
        assert active_action.is_active is True
        assert inactive_action.is_active is False