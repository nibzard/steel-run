"""WebSocket service for real-time status updates."""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from ..models.user import User

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}
        self.user_connections: dict[str, set[str]] = {}  # user_id -> set of connection_ids
        self.connection_users: dict[str, str] = {}       # connection_id -> user_id

    async def connect(self, websocket: WebSocket, user: User) -> str:
        """Accept a WebSocket connection and register it."""
        await websocket.accept()

        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket

        # Track user connections
        if user.id not in self.user_connections:
            self.user_connections[user.id] = set()
        self.user_connections[user.id].add(connection_id)
        self.connection_users[connection_id] = user.id

        logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            user_id=user.id,
            total_connections=len(self.active_connections)
        )

        return connection_id

    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Remove from user tracking
        if connection_id in self.connection_users:
            user_id = self.connection_users[connection_id]
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            del self.connection_users[connection_id]

        logger.info(
            "WebSocket connection closed",
            connection_id=connection_id,
            total_connections=len(self.active_connections)
        )

    async def send_personal_message(self, message: dict[str, Any], connection_id: str):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(
                    "Failed to send WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
                # Remove failed connection
                self.disconnect(connection_id)

    async def send_user_message(self, message: dict[str, Any], user_id: str):
        """Send a message to all connections for a specific user."""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])  # Create a copy
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)

    async def broadcast(self, message: dict[str, Any]):
        """Send a message to all active connections."""
        if not self.active_connections:
            return

        connection_ids = list(self.active_connections.keys())  # Create a copy
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self.user_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return len(self.active_connections)


class WebSocketService:
    """Service for managing WebSocket communications."""

    def __init__(self):
        """Initialize WebSocket service."""
        self.manager = ConnectionManager()

    async def handle_connection(self, websocket: WebSocket, user: User):
        """Handle a new WebSocket connection."""
        connection_id = await self.manager.connect(websocket, user)

        try:
            # Send welcome message
            await self.send_message(
                connection_id=connection_id,
                message_type="connection",
                data={
                    "status": "connected",
                    "connection_id": connection_id,
                    "user_id": user.id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Listen for messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_message(connection_id, user, message)
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await self.send_error(connection_id, "Invalid JSON message")
                except Exception as e:
                    logger.error(
                        "Error handling WebSocket message",
                        connection_id=connection_id,
                        error=str(e)
                    )
                    await self.send_error(connection_id, "Message processing failed")

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(
                "WebSocket connection error",
                connection_id=connection_id,
                error=str(e)
            )
        finally:
            self.manager.disconnect(connection_id)

    async def handle_message(self, connection_id: str, user: User, message: dict[str, Any]):
        """Handle incoming WebSocket message."""
        message_type = message.get("type")

        if message_type == "ping":
            await self.send_message(
                connection_id=connection_id,
                message_type="pong",
                data={"timestamp": datetime.utcnow().isoformat()}
            )

        elif message_type == "subscribe":
            # Handle subscription to specific events
            await self.handle_subscription(connection_id, user, message.get("data", {}))

        elif message_type == "unsubscribe":
            # Handle unsubscription
            await self.handle_unsubscription(connection_id, user, message.get("data", {}))

        else:
            await self.send_error(connection_id, f"Unknown message type: {message_type}")

    async def handle_subscription(self, connection_id: str, user: User, data: dict[str, Any]):
        """Handle subscription request."""
        subscription_type = data.get("type")

        # TODO: Implement subscription logic for different event types
        # For now, just acknowledge the subscription

        await self.send_message(
            connection_id=connection_id,
            message_type="subscription_confirmed",
            data={
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def handle_unsubscription(self, connection_id: str, user: User, data: dict[str, Any]):
        """Handle unsubscription request."""
        subscription_type = data.get("type")

        # TODO: Implement unsubscription logic

        await self.send_message(
            connection_id=connection_id,
            message_type="subscription_cancelled",
            data={
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def send_message(
        self,
        connection_id: str,
        message_type: str,
        data: dict[str, Any]
    ):
        """Send a formatted message to a connection."""
        message = {
            "type": message_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.manager.send_personal_message(message, connection_id)

    async def send_error(self, connection_id: str, error_message: str):
        """Send an error message to a connection."""
        await self.send_message(
            connection_id=connection_id,
            message_type="error",
            data={
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    # Event broadcasting methods

    async def broadcast_action_status_update(
        self,
        user_id: str,
        action_id: str,
        execution_id: str,
        status: str,
        progress: int | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        """Broadcast action execution status update to user."""
        message_data = {
            "action_id": action_id,
            "execution_id": execution_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if progress is not None:
            message_data["progress"] = progress

        if result is not None:
            message_data["result"] = result

        if error is not None:
            message_data["error"] = error

        await self.manager.send_user_message(
            message={
                "type": "action_status_update",
                "data": message_data,
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_id=user_id
        )

    async def broadcast_credential_validation_result(
        self,
        user_id: str,
        credential_id: str,
        is_valid: bool,
        validation_message: str,
    ):
        """Broadcast credential validation result to user."""
        await self.manager.send_user_message(
            message={
                "type": "credential_validation_result",
                "data": {
                    "credential_id": credential_id,
                    "is_valid": is_valid,
                    "validation_message": validation_message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                "timestamp": datetime.utcnow().isoformat(),
            },
            user_id=user_id
        )

    async def broadcast_system_notification(
        self,
        user_id: str | None,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
    ):
        """Broadcast a system notification."""
        notification_data = {
            "type": "system_notification",
            "data": {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if user_id:
            await self.manager.send_user_message(notification_data, user_id)
        else:
            await self.manager.broadcast(notification_data)

    def get_connection_stats(self) -> dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": self.manager.get_total_connections(),
            "unique_users": len(self.manager.user_connections),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global WebSocket service instance
websocket_service = WebSocketService()
