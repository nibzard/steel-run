"""Base class for all atomic web actions."""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import structlog
from steel import Steel

from ..core.config import settings

logger = structlog.get_logger(__name__)


class ActionExecutionError(Exception):
    """Base exception for action execution errors."""

    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        self.message = message
        self.error_code = error_code or "EXECUTION_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ActionValidationError(ActionExecutionError):
    """Exception for parameter validation errors."""

    def __init__(self, message: str, parameter: str | None = None):
        super().__init__(message, "VALIDATION_ERROR", {"parameter": parameter})


class ActionTimeoutError(ActionExecutionError):
    """Exception for action timeout errors."""

    def __init__(self, timeout_seconds: int):
        super().__init__(f"Action timed out after {timeout_seconds} seconds", "TIMEOUT_ERROR")


class BaseAction(ABC):
    """
    Base class for all atomic web actions.

    Each action should be self-contained and follow the pattern:
    Create Session → Execute → Release Session
    """

    # Metadata (must be overridden)
    name: str = "Base Action"
    description: str = "Base action class"
    parameters: dict[str, dict[str, Any]] = {}
    requires_auth: bool = False
    timeout_seconds: int = 30

    # Action categorization
    category: str = "general"
    tags: list[str] = []

    # Performance expectations
    estimated_duration_seconds: int = 10
    success_rate_threshold: float = 0.8

    def __init__(self):
        """Initialize the action with Steel client."""
        self.steel = Steel(steel_api_key=settings.steel_api_key)
        self.session_id: str | None = None
        self._start_time: float | None = None

    @abstractmethod
    async def execute(self, **params) -> dict[str, Any]:
        """
        Execute the atomic web action.

        Args:
            **params: Action parameters validated against self.parameters schema

        Returns:
            Dict containing:
                - status: "success" | "failed"
                - message: Human readable result message
                - data: Action-specific result data (optional)
                - screenshot: Base64 encoded screenshot (optional)
                - timestamp: ISO timestamp of completion

        Raises:
            ActionExecutionError: For execution failures
            ActionValidationError: For parameter validation failures
            ActionTimeoutError: For timeout errors
        """
        pass

    def validate_parameters(self, params: dict[str, Any]) -> None:
        """
        Validate input parameters against the action schema.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            ActionValidationError: If validation fails
        """
        for param_name, param_config in self.parameters.items():
            # Check required parameters
            if param_config.get("required", False) and param_name not in params:
                raise ActionValidationError(
                    f"Required parameter '{param_name}' missing",
                    parameter=param_name
                )

            # Skip validation for missing optional parameters
            if param_name not in params:
                continue

            value = params[param_name]
            param_type = param_config.get("type", "string")

            # Type validation
            if param_type == "string" and not isinstance(value, str):
                raise ActionValidationError(
                    f"Parameter '{param_name}' must be a string",
                    parameter=param_name
                )
            elif param_type == "integer" and not isinstance(value, int):
                raise ActionValidationError(
                    f"Parameter '{param_name}' must be an integer",
                    parameter=param_name
                )
            elif param_type == "boolean" and not isinstance(value, bool):
                raise ActionValidationError(
                    f"Parameter '{param_name}' must be a boolean",
                    parameter=param_name
                )
            elif param_type == "array" and not isinstance(value, list):
                raise ActionValidationError(
                    f"Parameter '{param_name}' must be an array",
                    parameter=param_name
                )

            # String length validation
            if param_type == "string" and isinstance(value, str):
                min_length = param_config.get("min_length")
                max_length = param_config.get("max_length")

                if min_length is not None and len(value) < min_length:
                    raise ActionValidationError(
                        f"Parameter '{param_name}' must be at least {min_length} characters",
                        parameter=param_name
                    )

                if max_length is not None and len(value) > max_length:
                    raise ActionValidationError(
                        f"Parameter '{param_name}' exceeds maximum length of {max_length}",
                        parameter=param_name
                    )

            # Integer range validation
            if param_type == "integer" and isinstance(value, int):
                min_value = param_config.get("min_value")
                max_value = param_config.get("max_value")

                if min_value is not None and value < min_value:
                    raise ActionValidationError(
                        f"Parameter '{param_name}' must be at least {min_value}",
                        parameter=param_name
                    )

                if max_value is not None and value > max_value:
                    raise ActionValidationError(
                        f"Parameter '{param_name}' must be at most {max_value}",
                        parameter=param_name
                    )

            # Array validation
            if param_type == "array" and isinstance(value, list):
                min_items = param_config.get("min_items")
                max_items = param_config.get("max_items")

                if min_items is not None and len(value) < min_items:
                    raise ActionValidationError(
                        f"Parameter '{param_name}' must have at least {min_items} items",
                        parameter=param_name
                    )

                if max_items is not None and len(value) > max_items:
                    raise ActionValidationError(
                        f"Parameter '{param_name}' must have at most {max_items} items",
                        parameter=param_name
                    )

    async def create_session(self, **session_options) -> str:
        """
        Create a Steel browser session for this action.

        Args:
            **session_options: Additional options for session creation

        Returns:
            str: Session ID
        """
        default_options = {
            "use_proxy": True,
            "solve_captcha": settings.enable_captcha_solving,
            "api_timeout": settings.default_session_timeout,
            "region": settings.default_region,
            "stealth_config": {
                "humanize_interactions": True,
                "skip_fingerprint_injection": False,
            },
            "block_ads": True,
        }

        # Merge with provided options
        options = {**default_options, **session_options}

        logger.info("Creating Steel browser session", action=self.name, options=options)

        try:
            session = self.steel.sessions.create(**options)
            self.session_id = session.id

            logger.info(
                "Steel session created successfully",
                action=self.name,
                session_id=self.session_id,
                websocket_url=session.websocket_url,
                debug_url=session.debug_url,
            )

            return self.session_id

        except Exception as e:
            logger.error("Failed to create Steel session", action=self.name, error=str(e))
            raise ActionExecutionError(
                f"Failed to create browser session: {str(e)}",
                error_code="SESSION_CREATION_ERROR"
            )

    async def release_session(self, session_id: str | None = None) -> None:
        """
        Release a Steel browser session.

        Args:
            session_id: Optional session ID to release. Uses self.session_id if not provided.
        """
        target_session_id = session_id or self.session_id

        if not target_session_id:
            logger.warning("No session ID provided for release", action=self.name)
            return

        try:
            self.steel.sessions.release(target_session_id)
            logger.info("Steel session released", action=self.name, session_id=target_session_id)

            if target_session_id == self.session_id:
                self.session_id = None

        except Exception as e:
            logger.warning(
                "Failed to release Steel session",
                action=self.name,
                session_id=target_session_id,
                error=str(e)
            )

    async def capture_screenshot(self, session_id: str | None = None, full_page: bool = True) -> str | None:
        """
        Capture a screenshot of the current browser state.

        Args:
            session_id: Optional session ID. Uses self.session_id if not provided.
            full_page: Whether to capture the full page or just viewport

        Returns:
            Optional[str]: Screenshot URL from Steel API, or None if failed
        """
        target_session_id = session_id or self.session_id

        if not target_session_id:
            logger.warning("No session ID for screenshot capture", action=self.name)
            return None

        try:
            # Use Steel's screenshot API
            screenshot_response = self.steel.screenshot(
                url="current",  # Current page in the session
                session_id=target_session_id,
                full_page=full_page,
                delay=1000  # Wait for page to settle
            )

            screenshot_url = screenshot_response.screenshot.url
            logger.info(
                "Screenshot captured successfully",
                action=self.name,
                session_id=target_session_id,
                screenshot_url=screenshot_url
            )

            return screenshot_url

        except Exception as e:
            logger.warning(
                "Failed to capture screenshot",
                action=self.name,
                session_id=target_session_id,
                error=str(e)
            )
            return None

    def get_metadata(self) -> dict[str, Any]:
        """
        Get action metadata for registration and discovery.

        Returns:
            Dict containing action metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires_auth": self.requires_auth,
            "timeout_seconds": self.timeout_seconds,
            "category": self.category,
            "tags": self.tags,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "success_rate_threshold": self.success_rate_threshold,
        }

    def preview_code(self) -> str:
        """
        Return readable code representation for editor view.

        Returns:
            str: Source code of the execute method
        """
        import inspect
        try:
            return inspect.getsource(self.execute)
        except Exception:
            return "# Code preview not available"

    async def execute_with_timeout(self, timeout_seconds: int | None = None, **params) -> dict[str, Any]:
        """
        Execute the action with a timeout wrapper.

        Args:
            timeout_seconds: Optional timeout override
            **params: Action parameters

        Returns:
            Dict: Execution result

        Raises:
            ActionTimeoutError: If execution times out
        """
        timeout = timeout_seconds or self.timeout_seconds

        try:
            return await asyncio.wait_for(self.execute(**params), timeout=timeout)
        except TimeoutError:
            logger.error("Action execution timed out", action=self.name, timeout=timeout)
            raise ActionTimeoutError(timeout)

    async def execute_safely(self, **params) -> dict[str, Any]:
        """
        Execute the action with comprehensive error handling and cleanup.

        This is the main entry point that should be used by the API layer.

        Args:
            **params: Action parameters

        Returns:
            Dict: Standardized execution result
        """
        self._start_time = time.time()
        execution_result = {
            "status": "failed",
            "message": "Unknown error occurred",
            "timestamp": datetime.now().isoformat(),
            "action_name": self.name,
            "execution_time_ms": 0,
        }


        try:
            # Validate parameters
            logger.info("Validating action parameters", action=self.name, params=list(params.keys()))
            self.validate_parameters(params)

            # Execute with timeout
            logger.info("Starting action execution", action=self.name)
            result = await self.execute_with_timeout(**params)

            # Ensure result has required fields
            execution_result.update({
                "status": result.get("status", "success"),
                "message": result.get("message", f"{self.name} completed successfully"),
                "data": result.get("data"),
                "screenshot": result.get("screenshot"),
                "timestamp": result.get("timestamp", datetime.now().isoformat()),
            })

            logger.info("Action execution completed", action=self.name, status=execution_result["status"])

        except ActionValidationError as e:
            execution_result.update({
                "status": "failed",
                "message": e.message,
                "error_code": e.error_code,
                "error_details": e.details,
            })
            logger.error("Action validation failed", action=self.name, error=e.message)

        except ActionTimeoutError as e:
            execution_result.update({
                "status": "timeout",
                "message": e.message,
                "error_code": e.error_code,
            })
            logger.error("Action execution timed out", action=self.name, timeout=self.timeout_seconds)

            # Capture timeout screenshot for debugging
            try:
                timeout_screenshot = await self.capture_screenshot()
                if timeout_screenshot:
                    execution_result["debug_screenshot"] = timeout_screenshot
            except Exception:
                pass  # Don't fail on debug screenshot

        except ActionExecutionError as e:
            execution_result.update({
                "status": "failed",
                "message": e.message,
                "error_code": e.error_code,
                "error_details": e.details,
            })
            logger.error("Action execution failed", action=self.name, error=e.message, code=e.error_code)

        except Exception as e:
            execution_result.update({
                "status": "failed",
                "message": f"Unexpected error: {str(e)}",
                "error_code": "UNEXPECTED_ERROR",
            })
            logger.exception("Unexpected error during action execution", action=self.name)

        finally:
            # Always attempt to clean up sessions
            await self._cleanup_resources()

            # Calculate execution time
            if self._start_time:
                execution_time_ms = int((time.time() - self._start_time) * 1000)
                execution_result["execution_time_ms"] = execution_time_ms

        return execution_result

    async def _cleanup_resources(self) -> None:
        """Clean up all resources used by this action."""
        cleanup_tasks = []

        # Release Steel session
        if self.session_id:
            cleanup_tasks.append(self.release_session())

        # Execute all cleanup tasks concurrently
        if cleanup_tasks:
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            # Log any cleanup failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        "Resource cleanup failed",
                        action=self.name,
                        cleanup_task=i,
                        error=str(result)
                    )
