"""WebSocket API endpoints for real-time updates."""

from typing import Any

import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from ...models.user import User
from ...services.websocket_service import websocket_service
from ..dependencies import get_current_user, get_websocket_user

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time communication.

    Clients should send authentication token in query parameters or headers.
    """
    try:
        # Get authenticated user
        user = await get_websocket_user(websocket)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            return

        # Handle the connection
        await websocket_service.handle_connection(websocket, user)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
        except Exception:
            pass  # Connection might already be closed


@router.get("/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Get WebSocket connection statistics.

    Returns information about active connections for monitoring purposes.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    stats = websocket_service.get_connection_stats()

    # Add user-specific connection count
    user_connections = websocket_service.manager.get_user_connection_count(current_user.id)
    stats["user_connections"] = user_connections

    return stats


@router.post("/broadcast/test")
async def test_broadcast(
    message: str,
    current_user: User = Depends(get_current_user)
):
    """
    Test endpoint for broadcasting messages (development only).

    Only available in debug mode for testing WebSocket functionality.
    """
    from ...core.config import settings

    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test endpoints only available in debug mode"
        )

    await websocket_service.broadcast_system_notification(
        user_id=current_user.id,
        notification_type="test",
        title="Test Notification",
        message=message,
        severity="info"
    )

    return {"status": "success", "message": "Test notification sent"}


@router.post("/notify/user/{user_id}")
async def send_user_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "general",
    severity: str = "info",
    current_user: User = Depends(get_current_user)
):
    """
    Send a notification to a specific user via WebSocket.

    This endpoint allows sending real-time notifications to users.
    """
    # TODO: Add authorization check - only allow admins or the user themselves
    if current_user.id != user_id:
        # For now, allow any authenticated user to send notifications
        # In production, this should be restricted to admins or specific roles
        pass

    await websocket_service.broadcast_system_notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        severity=severity
    )

    return {
        "status": "success",
        "message": f"Notification sent to user {user_id}"
    }


@router.post("/notify/broadcast")
async def broadcast_notification(
    title: str,
    message: str,
    notification_type: str = "system",
    severity: str = "info",
    current_user: User = Depends(get_current_user)
):
    """
    Broadcast a notification to all connected users.

    This endpoint allows sending system-wide notifications.
    Requires admin privileges in production.
    """
    # TODO: Add admin role check
    # For now, allow any authenticated user to broadcast

    await websocket_service.broadcast_system_notification(
        user_id=None,  # Broadcast to all users
        notification_type=notification_type,
        title=title,
        message=message,
        severity=severity
    )

    return {
        "status": "success",
        "message": "Notification broadcast to all users"
    }


# Additional WebSocket event endpoints that can be called by other services

async def notify_action_status_update(
    user_id: str,
    action_id: str,
    execution_id: str,
    status: str,
    progress: int = None,
    result: dict[str, Any] = None,
    error: str = None,
):
    """
    Notify user about action execution status update via WebSocket.

    This function is called by the execution service to provide real-time updates.
    """
    await websocket_service.broadcast_action_status_update(
        user_id=user_id,
        action_id=action_id,
        execution_id=execution_id,
        status=status,
        progress=progress,
        result=result,
        error=error,
    )


async def notify_credential_validation_result(
    user_id: str,
    credential_id: str,
    is_valid: bool,
    validation_message: str,
):
    """
    Notify user about credential validation result via WebSocket.

    This function is called by the credential service after validation.
    """
    await websocket_service.broadcast_credential_validation_result(
        user_id=user_id,
        credential_id=credential_id,
        is_valid=is_valid,
        validation_message=validation_message,
    )
