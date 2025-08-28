"""Tests for ExecutionRun model."""

import json
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_run import ExecutionRun


class TestExecutionRun:
    """Test ExecutionRun model."""

    @pytest.mark.asyncio
    async def test_create_execution_run(self, async_session: AsyncSession, twitter_stored_action):
        """Test creating a new execution run."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="running",
            steel_session_id="session_123",
            input_parameters=json.dumps({"message": "Hello World"}),
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.id is not None
        assert execution.stored_action_id == twitter_stored_action.id
        assert execution.user_id == twitter_stored_action.user_id
        assert execution.status == "running"
        assert execution.steel_session_id == "session_123"
        assert json.loads(execution.input_parameters) == {"message": "Hello World"}

    @pytest.mark.asyncio
    async def test_execution_run_defaults(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run default values."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="pending",
            steel_session_id="session_123",
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.webhook_delivered is None
        assert execution.webhook_response_status is None
        assert execution.error_message is None

    @pytest.mark.asyncio
    async def test_execution_run_timestamps(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run timestamp fields."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="pending",
            steel_session_id="session_123",
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.created_at is not None
        assert execution.updated_at is not None
        assert isinstance(execution.created_at, datetime)
        assert isinstance(execution.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_execution_run_completion_timestamps(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run completion timestamp fields."""
        now = datetime.utcnow()
        
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            started_at=now,
            completed_at=now,
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.started_at == now
        assert execution.completed_at == now

    @pytest.mark.asyncio
    async def test_execution_run_success_result(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run with successful result."""
        result_data = {"success": True, "tweet_id": "123456789"}
        
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            steel_action_run_id="run_456",
            result_data=json.dumps(result_data),
            execution_time_ms=2500,
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.status == "completed"
        assert execution.steel_action_run_id == "run_456"
        assert json.loads(execution.result_data) == result_data
        assert execution.execution_time_ms == 2500

    @pytest.mark.asyncio
    async def test_execution_run_failure_result(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run with failed result."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="failed",
            steel_session_id="session_123",
            error_message="Rate limit exceeded",
            execution_time_ms=1000,
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.status == "failed"
        assert execution.error_message == "Rate limit exceeded"
        assert execution.execution_time_ms == 1000

    @pytest.mark.asyncio
    async def test_execution_run_screenshots(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run with screenshots."""
        screenshots = ["https://example.com/screenshot1.png", "https://example.com/screenshot2.png"]
        
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            screenshots_urls=json.dumps(screenshots),
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert json.loads(execution.screenshots_urls) == screenshots

    @pytest.mark.asyncio
    async def test_execution_run_logs(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run with logs."""
        logs = ["Started action", "Navigating to Twitter", "Posting tweet", "Action completed"]
        
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            logs=json.dumps(logs),
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert json.loads(execution.logs) == logs

    @pytest.mark.asyncio
    async def test_execution_run_webhook_delivery(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run webhook delivery tracking."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            webhook_delivered=True,
            webhook_response_status=200,
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.webhook_delivered is True
        assert execution.webhook_response_status == 200

    @pytest.mark.asyncio
    async def test_execution_run_webhook_delivery_failed(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run webhook delivery failure."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            webhook_delivered=False,
            webhook_response_status=500,
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        assert execution.webhook_delivered is False
        assert execution.webhook_response_status == 500

    @pytest.mark.asyncio
    async def test_execution_run_relationships(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run relationships with other models."""
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        # Test relationships exist
        assert hasattr(execution, 'stored_action')
        assert hasattr(execution, 'user')

    @pytest.mark.asyncio
    async def test_execution_run_status_values(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run with different status values."""
        statuses = ["pending", "running", "completed", "failed", "cancelled"]
        
        executions = []
        for i, status in enumerate(statuses):
            execution = ExecutionRun(
                stored_action_id=twitter_stored_action.id,
                user_id=twitter_stored_action.user_id,
                status=status,
                steel_session_id=f"session_{i}",
            )
            executions.append(execution)
        
        async_session.add_all(executions)
        await async_session.commit()
        
        for i, execution in enumerate(executions):
            await async_session.refresh(execution)
            assert execution.status == statuses[i]

    @pytest.mark.asyncio
    async def test_execution_run_input_parameters(self, async_session: AsyncSession, twitter_stored_action):
        """Test execution run with various input parameters."""
        complex_params = {
            "message": "Hello World",
            "options": {
                "include_timestamp": True,
                "use_thread": False,
                "tags": ["automation", "test"]
            },
            "retry_count": 3,
        }
        
        execution = ExecutionRun(
            stored_action_id=twitter_stored_action.id,
            user_id=twitter_stored_action.user_id,
            status="completed",
            steel_session_id="session_123",
            input_parameters=json.dumps(complex_params),
        )
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)

        parsed_params = json.loads(execution.input_parameters)
        assert parsed_params == complex_params
        assert parsed_params["options"]["include_timestamp"] is True
        assert "automation" in parsed_params["options"]["tags"]