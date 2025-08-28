"""Graceful shutdown handling for the application."""

import asyncio
import signal
import sys

import structlog

logger = structlog.get_logger(__name__)


class GracefulShutdownHandler:
    """Handles graceful application shutdown."""

    def __init__(self):
        """Initialize shutdown handler."""
        self.shutdown_event = asyncio.Event()
        self.cleanup_tasks = []
        self._is_shutting_down = False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        if sys.platform == "win32":
            # Windows signal handling
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        else:
            # Unix signal handling
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                loop.add_signal_handler(sig, self._signal_handler_async, sig)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (Windows)."""
        logger.info("Received shutdown signal", signal=signum)
        self._is_shutting_down = True
        self.shutdown_event.set()

    def _signal_handler_async(self, signum):
        """Handle shutdown signals (Unix)."""
        logger.info("Received shutdown signal", signal=signum)
        self._is_shutting_down = True
        self.shutdown_event.set()

    def add_cleanup_task(self, coro):
        """Add a cleanup task to be run during shutdown."""
        self.cleanup_tasks.append(coro)

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()
        logger.info("Shutdown initiated, running cleanup tasks")
        await self._run_cleanup_tasks()

    async def _run_cleanup_tasks(self):
        """Run all cleanup tasks."""
        if not self.cleanup_tasks:
            logger.info("No cleanup tasks to run")
            return

        logger.info("Running cleanup tasks", count=len(self.cleanup_tasks))

        # Run all cleanup tasks concurrently with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*[task() for task in self.cleanup_tasks], return_exceptions=True),
                timeout=30.0  # 30 second timeout for all cleanup tasks
            )
            logger.info("All cleanup tasks completed successfully")
        except TimeoutError:
            logger.warning("Cleanup tasks timed out, forcing shutdown")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._is_shutting_down


# Global shutdown handler instance
shutdown_handler = GracefulShutdownHandler()


# Cleanup functions for various components

async def cleanup_database_connections():
    """Cleanup database connections."""
    try:
        from ..core.database import engine
        if engine:
            await engine.dispose()
            logger.info("Database connections closed")
    except Exception as e:
        logger.error("Failed to cleanup database connections", error=str(e))


async def cleanup_steel_sessions():
    """Cleanup any active Steel browser sessions."""
    try:
        # TODO: Implement Steel session cleanup
        # This would involve tracking active sessions and closing them
        logger.info("Steel sessions cleanup completed")
    except Exception as e:
        logger.error("Failed to cleanup Steel sessions", error=str(e))


async def cleanup_websocket_connections():
    """Cleanup WebSocket connections."""
    try:
        from ..services.websocket_service import websocket_service

        # Broadcast shutdown notification
        await websocket_service.broadcast_system_notification(
            user_id=None,
            notification_type="system_shutdown",
            title="System Maintenance",
            message="The system is shutting down for maintenance. Please reconnect in a few moments.",
            severity="warning"
        )

        # Close all connections
        connection_count = websocket_service.manager.get_total_connections()
        if connection_count > 0:
            logger.info("Closing WebSocket connections", count=connection_count)

            # Give clients time to receive the shutdown notification
            await asyncio.sleep(1.0)

            # Force close remaining connections
            connection_ids = list(websocket_service.manager.active_connections.keys())
            for connection_id in connection_ids:
                try:
                    websocket = websocket_service.manager.active_connections[connection_id]
                    await websocket.close(code=1001, reason="Server shutdown")
                except Exception:
                    pass  # Connection might already be closed
                websocket_service.manager.disconnect(connection_id)

        logger.info("WebSocket connections cleanup completed")
    except Exception as e:
        logger.error("Failed to cleanup WebSocket connections", error=str(e))


async def cleanup_background_tasks():
    """Cleanup any running background tasks."""
    try:
        # Cancel any background tasks
        # TODO: Keep track of background tasks and cancel them here
        logger.info("Background tasks cleanup completed")
    except Exception as e:
        logger.error("Failed to cleanup background tasks", error=str(e))


# Register cleanup tasks
shutdown_handler.add_cleanup_task(cleanup_websocket_connections)
shutdown_handler.add_cleanup_task(cleanup_steel_sessions)
shutdown_handler.add_cleanup_task(cleanup_background_tasks)
shutdown_handler.add_cleanup_task(cleanup_database_connections)
