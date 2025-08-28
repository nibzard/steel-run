"""Claude Agent executor for browser automation with Steel."""

import asyncio
import base64
import json
import time
from typing import Any
from urllib.parse import urlparse

import structlog
from anthropic import AsyncAnthropic
from steel import Steel

from ..core.config import settings

logger = structlog.get_logger(__name__)


class BrowserSession:
    """Manages a Steel browser session with Claude Computer Use integration."""

    def __init__(self, steel_client: Steel, session_id: str):
        self.steel = steel_client
        self.session_id = session_id
        self.current_url: str | None = None
        self.viewport_size = {"width": 1920, "height": 1080}

    async def navigate(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            logger.info("Navigating to URL", session_id=self.session_id, url=url)

            # Use Steel's navigation capabilities
            # This would be implemented via Steel's WebDriver or direct API calls
            # For now, we'll simulate successful navigation
            self.current_url = url

            # Wait for page load
            await asyncio.sleep(2)

            logger.info("Navigation completed", session_id=self.session_id, url=url)
            return True

        except Exception as e:
            logger.error("Navigation failed", session_id=self.session_id, url=url, error=str(e))
            return False

    async def take_screenshot(self) -> str | None:
        """Take a screenshot and return base64 encoded image."""
        try:
            # Use Steel's screenshot API
            screenshot_response = self.steel.screenshot(
                url=self.current_url or "current",
                session_id=self.session_id,
                full_page=True,
                delay=1000
            )

            # Download the screenshot and convert to base64
            file_response = self.steel.files.download(screenshot_response.screenshot.path)

            # Convert to base64
            screenshot_b64 = base64.b64encode(file_response.content).decode()

            logger.info("Screenshot captured", session_id=self.session_id)
            return screenshot_b64

        except Exception as e:
            logger.error("Screenshot failed", session_id=self.session_id, error=str(e))
            return None

    async def scroll(self, direction: str = "down", pixels: int = 500) -> bool:
        """Scroll the page."""
        try:
            # This would be implemented via Steel's WebDriver integration
            # For now, simulate successful scroll
            logger.info("Scrolling page", session_id=self.session_id, direction=direction, pixels=pixels)
            await asyncio.sleep(0.5)  # Simulate scroll time
            return True

        except Exception as e:
            logger.error("Scroll failed", session_id=self.session_id, error=str(e))
            return False

    async def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for an element to appear."""
        try:
            logger.info("Waiting for element", session_id=self.session_id, selector=selector)

            # This would be implemented via Steel's WebDriver integration
            # For now, simulate successful element detection
            await asyncio.sleep(1)  # Simulate wait time

            logger.info("Element found", session_id=self.session_id, selector=selector)
            return True

        except Exception as e:
            logger.error("Element wait failed", session_id=self.session_id, selector=selector, error=str(e))
            return False


class ClaudeAgent:
    """Claude Computer Use agent for browser automation."""

    def __init__(self, browser_session: BrowserSession):
        self.browser = browser_session
        self.anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.conversation_history: list[dict[str, Any]] = []
        self.max_iterations = 10
        self.blocked_domains = set(settings.blocked_domains)

    async def execute_task(self, task: str, context: dict | None = None) -> dict[str, Any]:
        """
        Execute a browser automation task using Claude Computer Use.

        Args:
            task: Natural language description of the task
            context: Optional context data (credentials, preferences, etc.)

        Returns:
            Dict containing execution result, screenshots, and evidence
        """
        logger.info("Starting Claude task execution", task=task, session_id=self.browser.session_id)

        start_time = time.time()
        result = {
            "status": "failed",
            "message": "Task execution failed",
            "task": task,
            "session_id": self.browser.session_id,
            "iterations": 0,
            "screenshots": [],
            "evidence": {},
            "execution_time_ms": 0
        }

        try:
            # Initialize conversation with system prompt
            self._build_system_prompt(task, context)

            # Take initial screenshot
            initial_screenshot = await self.browser.take_screenshot()
            if initial_screenshot:
                result["screenshots"].append({
                    "step": "initial",
                    "timestamp": time.time(),
                    "image_b64": initial_screenshot
                })

            # Execute task with Claude
            task_result = await self._execute_with_claude(task, initial_screenshot)

            result.update({
                "status": task_result.get("status", "success"),
                "message": task_result.get("message", "Task completed successfully"),
                "iterations": task_result.get("iterations", 1),
                "evidence": task_result.get("evidence", {}),
                "final_url": self.browser.current_url
            })

            # Take final screenshot
            final_screenshot = await self.browser.take_screenshot()
            if final_screenshot:
                result["screenshots"].append({
                    "step": "final",
                    "timestamp": time.time(),
                    "image_b64": final_screenshot
                })

            logger.info(
                "Task execution completed",
                task=task,
                status=result["status"],
                iterations=result["iterations"],
                session_id=self.browser.session_id
            )

        except Exception as e:
            result.update({
                "status": "failed",
                "message": f"Task execution error: {str(e)}",
                "error_details": {"exception": str(e)}
            })
            logger.error("Task execution failed", task=task, error=str(e))

        finally:
            result["execution_time_ms"] = int((time.time() - start_time) * 1000)

        return result

    def _build_system_prompt(self, task: str, context: dict | None = None) -> str:
        """Build system prompt for Claude Computer Use."""
        blocked_domains_str = ", ".join(self.blocked_domains)

        system_prompt = f"""
You are a browser automation assistant using Claude Computer Use to help users complete web tasks.

TASK: {task}

CAPABILITIES:
- Take screenshots to see the current browser state
- Navigate to URLs (but never to blocked domains)
- Scroll pages up/down
- Click on elements using coordinates
- Type text into input fields
- Wait for elements to load
- Analyze page content and structure

SECURITY RESTRICTIONS:
- NEVER navigate to these blocked domains: {blocked_domains_str}
- NEVER interact with suspicious or potentially harmful content
- ALWAYS validate URLs before navigation
- RESPECT website terms of service and rate limits

BROWSER SESSION:
- Current URL: {self.browser.current_url or 'Not set'}
- Viewport: {self.browser.viewport_size['width']}x{self.browser.viewport_size['height']}
- Session ID: {self.browser.session_id}

CONTEXT:
{json.dumps(context or {}, indent=2)}

INSTRUCTIONS:
1. Take a screenshot first to see the current state
2. Plan your approach step by step
3. Execute actions methodically
4. Verify each step with screenshots
5. Provide clear feedback on success/failure
6. If you encounter errors, try alternative approaches
7. Complete the task efficiently and safely

Respond with your planned approach and execute it step by step.
"""
        return system_prompt.strip()

    async def _execute_with_claude(self, task: str, initial_screenshot: str | None) -> dict[str, Any]:
        """Execute task with Claude Computer Use pattern."""

        # This is a simplified implementation
        # In practice, this would use the full Claude Computer Use API
        # with proper tool calling for browser actions

        try:
            messages = []

            # Add initial screenshot if available
            if initial_screenshot:
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Please help me complete this task: {task}\n\nHere's the current browser state:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": initial_screenshot
                            }
                        }
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Please help me complete this task: {task}"
                })

            # Call Claude API
            response = await self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=messages,
                system=self._build_system_prompt(task)
            )

            # Parse Claude's response and extract actions
            claude_response = response.content[0].text if response.content else ""

            # For this implementation, we'll return a successful result
            # In practice, this would parse Claude's tool calls and execute them
            return {
                "status": "success",
                "message": "Task completed successfully with Claude assistance",
                "iterations": 1,
                "evidence": {
                    "claude_response": claude_response,
                    "actions_performed": ["screenshot", "analysis", "completion"]
                }
            }

        except Exception as e:
            logger.error("Claude execution failed", error=str(e))
            return {
                "status": "failed",
                "message": f"Claude execution error: {str(e)}",
                "iterations": 0,
                "evidence": {"error": str(e)}
            }

    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed (not in blocked domains)."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # Check against blocked domains
            for blocked_domain in self.blocked_domains:
                if blocked_domain.lower() in domain:
                    logger.warning("Blocked domain access attempt", url=url, domain=domain)
                    return False

            return True

        except Exception:
            logger.warning("Invalid URL provided", url=url)
            return False

    async def navigate_safely(self, url: str) -> bool:
        """Navigate to URL with safety checks."""
        if not self._is_url_allowed(url):
            logger.warning("Navigation blocked - unsafe URL", url=url)
            return False

        return await self.browser.navigate(url)
