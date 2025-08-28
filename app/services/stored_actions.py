"""Service layer for stored actions management."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.execution_run import ExecutionRun, ExecutionStatus
from ..models.stored_action import StoredAction
from ..schemas.stored_action import StoredActionCreate, StoredActionUpdate


class StoredActionService:
    """Service class for stored action operations."""

    @staticmethod
    async def create_stored_action(
        db: AsyncSession, user_id: str, action_data: StoredActionCreate
    ) -> StoredAction:
        """
        Create a new stored action.

        Args:
            db: Database session
            user_id: User ID
            action_data: Action creation data

        Returns:
            Created stored action instance
        """
        # Serialize parameters
        parameters_json = json.dumps(action_data.parameters) if action_data.parameters else "{}"
        tags_json = json.dumps(action_data.tags) if action_data.tags else None

        stored_action = StoredAction(
            user_id=user_id,
            name=action_data.name,
            description=action_data.description,
            action_type=action_data.action_type,
            parameters=parameters_json,
            webhook_url=str(action_data.webhook_url) if action_data.webhook_url else None,
            is_active=action_data.is_active,
            is_public=action_data.is_public,
            tags=tags_json,
        )

        db.add(stored_action)
        await db.commit()
        await db.refresh(stored_action)

        return stored_action

    @staticmethod
    async def get_user_actions(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
        action_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[StoredAction], int]:
        """
        Get stored actions for a user with pagination and filtering.

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: Whether to return only active actions
            action_type: Filter by action type
            search: Search in name and description

        Returns:
            Tuple of (actions list, total count)
        """
        # Build query conditions
        conditions = [StoredAction.user_id == user_id]

        if active_only:
            conditions.append(StoredAction.is_active)

        if action_type:
            conditions.append(StoredAction.action_type == action_type)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                StoredAction.name.ilike(search_pattern) |
                StoredAction.description.ilike(search_pattern)
            )

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(StoredAction).where(and_(*conditions))
        )
        total = count_result.scalar()

        # Get actions
        result = await db.execute(
            select(StoredAction)
            .where(and_(*conditions))
            .order_by(desc(StoredAction.updated_at))
            .offset(skip)
            .limit(limit)
        )
        actions = result.scalars().all()

        return actions, total

    @staticmethod
    async def get_stored_action(
        db: AsyncSession, user_id: str, action_id: str
    ) -> StoredAction | None:
        """
        Get a stored action by ID for a specific user.

        Args:
            db: Database session
            user_id: User ID
            action_id: Action ID

        Returns:
            Stored action instance if found, None otherwise
        """
        result = await db.execute(
            select(StoredAction)
            .where(StoredAction.id == action_id, StoredAction.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_stored_action_by_id(
        db: AsyncSession, action_id: str
    ) -> StoredAction | None:
        """
        Get a stored action by ID (for API execution).

        Args:
            db: Database session
            action_id: Action ID

        Returns:
            Stored action instance if found, None otherwise
        """
        result = await db.execute(
            select(StoredAction).where(StoredAction.id == action_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_stored_action(
        db: AsyncSession, user_id: str, action_id: str, action_data: StoredActionUpdate
    ) -> StoredAction | None:
        """
        Update a stored action.

        Args:
            db: Database session
            user_id: User ID
            action_id: Action ID
            action_data: Update data

        Returns:
            Updated stored action instance if found, None otherwise
        """
        stored_action = await StoredActionService.get_stored_action(db, user_id, action_id)
        if not stored_action:
            return None

        # Update fields
        update_data = action_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "parameters" and value is not None:
                setattr(stored_action, field, json.dumps(value))
            elif field == "tags" and value is not None:
                setattr(stored_action, field, json.dumps(value))
            elif field == "webhook_url" and value is not None:
                setattr(stored_action, field, str(value))
            else:
                setattr(stored_action, field, value)

        # Increment version
        stored_action.version += 1

        await db.commit()
        await db.refresh(stored_action)

        return stored_action

    @staticmethod
    async def delete_stored_action(
        db: AsyncSession, user_id: str, action_id: str
    ) -> bool:
        """
        Delete a stored action.

        Args:
            db: Database session
            user_id: User ID
            action_id: Action ID

        Returns:
            True if deleted successfully, False otherwise
        """
        stored_action = await StoredActionService.get_stored_action(db, user_id, action_id)
        if not stored_action:
            return False

        await db.delete(stored_action)
        await db.commit()

        return True

    @staticmethod
    async def create_execution_run(
        db: AsyncSession,
        stored_action: StoredAction,
        user_id: str,
        input_parameters: dict[str, Any] | None = None,
        webhook_url: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 0,
        external_request_id: str | None = None,
        triggered_by: str = "api",
    ) -> ExecutionRun:
        """
        Create a new execution run for a stored action.

        Args:
            db: Database session
            stored_action: Stored action to execute
            user_id: User ID
            input_parameters: Override parameters for this execution
            webhook_url: Override webhook URL for this execution
            timeout_seconds: Execution timeout
            max_retries: Maximum retry attempts
            external_request_id: External service request ID
            triggered_by: How execution was triggered

        Returns:
            Created execution run instance
        """
        # Use action parameters as base, override with input parameters
        base_parameters = json.loads(stored_action.parameters)
        final_parameters = {**base_parameters, **(input_parameters or {})}

        execution_run = ExecutionRun(
            stored_action_id=stored_action.id,
            user_id=user_id,
            input_parameters=json.dumps(final_parameters),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            external_request_id=external_request_id,
            triggered_by=triggered_by,
            webhook_url=webhook_url or stored_action.webhook_url,
        )

        db.add(execution_run)
        await db.commit()
        await db.refresh(execution_run)

        return execution_run

    @staticmethod
    async def get_execution_run(
        db: AsyncSession, action_id: str, run_id: str
    ) -> ExecutionRun | None:
        """
        Get an execution run by ID.

        Args:
            db: Database session
            action_id: Action ID
            run_id: Run ID

        Returns:
            Execution run instance if found, None otherwise
        """
        result = await db.execute(
            select(ExecutionRun)
            .where(
                ExecutionRun.id == run_id,
                ExecutionRun.stored_action_id == action_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_execution_runs(
        db: AsyncSession,
        user_id: str,
        action_id: str | None = None,
        status: ExecutionStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ExecutionRun], int]:
        """
        Get execution runs for a user with filtering.

        Args:
            db: Database session
            user_id: User ID
            action_id: Optional action ID filter
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (execution runs list, total count)
        """
        # Build query conditions
        conditions = [ExecutionRun.user_id == user_id]

        if action_id:
            conditions.append(ExecutionRun.stored_action_id == action_id)

        if status:
            conditions.append(ExecutionRun.status == status)

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(ExecutionRun).where(and_(*conditions))
        )
        total = count_result.scalar()

        # Get execution runs
        result = await db.execute(
            select(ExecutionRun)
            .where(and_(*conditions))
            .order_by(desc(ExecutionRun.created_at))
            .offset(skip)
            .limit(limit)
        )
        runs = result.scalars().all()

        return runs, total

    @staticmethod
    async def update_execution_status(
        db: AsyncSession,
        run_id: str,
        status: ExecutionStatus,
        result_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        error_code: str | None = None,
        screenshot_url: str | None = None,
        pdf_url: str | None = None,
        session_id: str | None = None,
        session_region: str | None = None,
        credits_used: int | None = None,
    ) -> ExecutionRun | None:
        """
        Update execution run status and results.

        Args:
            db: Database session
            run_id: Run ID
            status: New status
            result_data: Execution results
            error_message: Error message if failed
            error_code: Error code if failed
            screenshot_url: Screenshot URL
            pdf_url: PDF URL
            session_id: Steel session ID
            session_region: Steel session region
            credits_used: Steel credits consumed

        Returns:
            Updated execution run instance if found, None otherwise
        """
        result = await db.execute(
            select(ExecutionRun).where(ExecutionRun.id == run_id)
        )
        execution_run = result.scalar_one_or_none()

        if not execution_run:
            return None

        # Update status
        execution_run.status = status

        # Update completion time if finished
        if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]:
            execution_run.completed_at = datetime.utcnow()
            execution_run.execution_time = execution_run.duration_ms

        # Update result data
        if result_data:
            execution_run.result_data = json.dumps(result_data)

        # Update error information
        if error_message:
            execution_run.error_message = error_message
        if error_code:
            execution_run.error_code = error_code

        # Update Steel session information
        if session_id:
            execution_run.session_id = session_id
        if session_region:
            execution_run.session_region = session_region
        if credits_used:
            execution_run.credits_used = credits_used

        # Update output URLs
        if screenshot_url:
            execution_run.screenshot_url = screenshot_url
        if pdf_url:
            execution_run.pdf_url = pdf_url

        await db.commit()
        await db.refresh(execution_run)

        # Update stored action statistics
        if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
            await StoredActionService._update_action_stats(
                db, execution_run.stored_action_id, status == ExecutionStatus.COMPLETED
            )

        return execution_run

    @staticmethod
    async def _update_action_stats(
        db: AsyncSession, action_id: str, success: bool
    ) -> None:
        """
        Update stored action statistics after execution.

        Args:
            db: Database session
            action_id: Action ID
            success: Whether execution was successful
        """
        result = await db.execute(
            select(StoredAction).where(StoredAction.id == action_id)
        )
        stored_action = result.scalar_one_or_none()

        if not stored_action:
            return

        # Get latest execution for timing
        result = await db.execute(
            select(ExecutionRun)
            .where(ExecutionRun.stored_action_id == action_id)
            .order_by(desc(ExecutionRun.completed_at))
            .limit(1)
        )
        latest_run = result.scalar_one_or_none()

        if latest_run and latest_run.execution_time:
            stored_action.update_stats(success, latest_run.execution_time)
        else:
            stored_action.update_stats(success, 0)

        await db.commit()
