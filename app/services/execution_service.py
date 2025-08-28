"""Asynchronous action execution service."""

import asyncio
import json
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from steel import Steel

from ..core.config import settings
from ..core.database import async_session_factory
from ..models.execution_run import ExecutionRun
from ..schemas.stored_action import WebhookPayload
from .stored_actions import StoredActionService

logger = structlog.get_logger(__name__)


class ExecutionService:
    """Service for executing stored actions asynchronously."""

    @staticmethod
    async def execute_action_async(run_id: str) -> None:
        """
        Execute a stored action asynchronously.

        This method is designed to be called from a background task queue
        like Celery or as an asyncio task.

        Args:
            run_id: Execution run ID
        """
        async with async_session_factory() as db:
            try:
                # Get execution run
                execution_run = await ExecutionService._get_execution_run(db, run_id)
                if not execution_run:
                    logger.error("Execution run not found", run_id=run_id)
                    return

                # Mark as started
                execution_run.mark_started()
                await db.commit()

                # Send start webhook if configured
                await ExecutionService._send_webhook(execution_run, "execution.started")

                # Execute the action
                result_data = await ExecutionService._execute_action(execution_run)

                # Mark as completed
                execution_run.mark_completed(result_data)
                await db.commit()

                # Update stored action statistics
                await StoredActionService._update_action_stats(
                    db, execution_run.stored_action_id, True
                )

                # Send completion webhook
                await ExecutionService._send_webhook(execution_run, "execution.completed")

                logger.info(
                    "Action executed successfully",
                    run_id=run_id,
                    action_id=execution_run.stored_action_id,
                    execution_time=execution_run.execution_time,
                )

            except Exception as e:
                logger.error(
                    "Action execution failed",
                    run_id=run_id,
                    error=str(e),
                    exc_info=True,
                )

                # Mark as failed
                if execution_run:
                    execution_run.mark_failed(str(e), "EXECUTION_ERROR")
                    await db.commit()

                    # Update stored action statistics
                    await StoredActionService._update_action_stats(
                        db, execution_run.stored_action_id, False
                    )

                    # Send failure webhook
                    await ExecutionService._send_webhook(execution_run, "execution.failed")

    @staticmethod
    async def _get_execution_run(db: AsyncSession, run_id: str) -> ExecutionRun | None:
        """Get execution run by ID."""
        from sqlalchemy import select

        result = await db.execute(
            select(ExecutionRun).where(ExecutionRun.id == run_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _execute_action(execution_run: ExecutionRun) -> dict[str, Any]:
        """
        Execute the actual action using Steel SDK.

        Args:
            execution_run: Execution run instance

        Returns:
            Action execution results
        """
        # Parse input parameters
        parameters = json.loads(execution_run.input_parameters or "{}")

        # Get stored action to determine action type
        async with async_session_factory() as db:
            stored_action = await StoredActionService.get_stored_action_by_id(
                db, execution_run.stored_action_id
            )

            if not stored_action:
                raise ValueError("Stored action not found")

            action_type = stored_action.action_type

        # Get action class from registry
        if not action_registry.is_registered(action_type):
            raise ValueError(f"Unknown action type: {action_type}")

        action_class = action_registry.get_action(action_type)

        # Create action instance
        action = action_class(**parameters)

        # Execute with Steel
        async with Steel() as steel:
            try:
                # Create session with appropriate settings
                user = await ExecutionService._get_user_by_id(execution_run.user_id)
                region = user.default_region if user else settings.default_region

                session = await steel.sessions.create(
                    region=region,
                    timeout=execution_run.timeout_seconds * 1000,  # Convert to milliseconds
                    solve_captcha=settings.enable_captcha_solving,
                )

                execution_run.session_id = session.id
                execution_run.session_region = region

                # Execute action
                result = await action.execute(steel, session)

                # Capture outputs if enabled
                if user and user.enable_screenshots:
                    try:
                        screenshot_data = await steel.sessions.screenshot(session.id, format="base64")
                        execution_run.screenshot_data = screenshot_data
                    except Exception as e:
                        logger.warning("Failed to capture screenshot", error=str(e))

                # Get session usage info (if available)
                try:
                    session_info = await steel.sessions.get(session.id)
                    if hasattr(session_info, 'credits_used'):
                        execution_run.credits_used = session_info.credits_used
                except Exception:
                    pass

                # Release session
                await steel.sessions.release(session.id)

                return result

            except Exception as e:
                # Try to release session on error
                try:
                    if execution_run.session_id:
                        await steel.sessions.release(execution_run.session_id)
                except Exception:
                    pass

                raise e

    @staticmethod
    async def _get_user_by_id(user_id: str):
        """Get user by ID for execution settings."""
        async with async_session_factory() as db:
            from ..services.auth_service import AuthService
            return await AuthService.get_user_by_id(db, user_id)

    @staticmethod
    async def _send_webhook(execution_run: ExecutionRun, event_type: str) -> None:
        """
        Send webhook notification for execution event.

        Args:
            execution_run: Execution run instance
            event_type: Event type (execution.started, execution.completed, execution.failed)
        """
        if not execution_run.webhook_url or not settings.enable_webhooks:
            return

        try:
            # Get stored action for webhook payload
            async with async_session_factory() as db:
                stored_action = await StoredActionService.get_stored_action_by_id(
                    db, execution_run.stored_action_id
                )

            if not stored_action:
                return

            # Create webhook payload
            payload_data = {
                "event_type": event_type,
                "timestamp": execution_run.updated_at.isoformat(),
                "run_id": execution_run.id,
                "action_id": execution_run.stored_action_id,
                "action_name": stored_action.name,
                "status": execution_run.status,
                "external_request_id": execution_run.external_request_id,
            }

            # Add execution-specific data
            if event_type in ["execution.completed", "execution.failed"]:
                payload_data["execution_time"] = execution_run.execution_time

                if execution_run.result_data:
                    payload_data["result_data"] = json.loads(execution_run.result_data)

                if execution_run.error_message:
                    payload_data["error_message"] = execution_run.error_message
                    payload_data["error_code"] = execution_run.error_code

            webhook_payload = WebhookPayload(**payload_data)

            # Send webhook
            async with httpx.AsyncClient(timeout=settings.webhook_timeout) as client:
                response = await client.post(
                    execution_run.webhook_url,
                    json=webhook_payload.dict(),
                    headers={"Content-Type": "application/json"},
                )

                # Update webhook status
                async with async_session_factory() as db:
                    run = await ExecutionService._get_execution_run(db, execution_run.id)
                    if run:
                        run.webhook_sent = True
                        run.webhook_response_code = response.status_code
                        run.webhook_attempts += 1
                        await db.commit()

                logger.info(
                    "Webhook sent successfully",
                    run_id=execution_run.id,
                    event_type=event_type,
                    webhook_url=execution_run.webhook_url,
                    status_code=response.status_code,
                )

        except Exception as e:
            logger.error(
                "Failed to send webhook",
                run_id=execution_run.id,
                event_type=event_type,
                webhook_url=execution_run.webhook_url,
                error=str(e),
            )

            # Update webhook failure status
            try:
                async with async_session_factory() as db:
                    run = await ExecutionService._get_execution_run(db, execution_run.id)
                    if run:
                        run.webhook_attempts += 1
                        await db.commit()
            except Exception:
                pass


async def queue_action_execution(run_id: str) -> None:
    """
    Queue an action for execution.

    In a production environment, this would submit the task to a queue
    like Celery. For now, we'll execute it as an asyncio task.

    Args:
        run_id: Execution run ID
    """
    # For development/testing, execute in background task
    asyncio.create_task(ExecutionService.execute_action_async(run_id))

    logger.info("Action execution queued", run_id=run_id)
