"""Twitter automation actions using Steel and Claude Computer Use."""

import time
from typing import Any

import structlog

from ..agent.executor import BrowserSession, ClaudeAgent
from .base import ActionExecutionError, ActionValidationError, BaseAction

logger = structlog.get_logger(__name__)


class TwitterPostAction(BaseAction):
    """Post a tweet to Twitter/X.com using browser automation."""

    # Action metadata
    name = "Post to Twitter"
    description = "Post a tweet to your Twitter timeline"
    category = "social_media"
    tags = ["twitter", "x", "social", "posting"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 60  # Twitter can be slow
    estimated_duration_seconds = 30
    success_rate_threshold = 0.85

    # Parameter schema
    parameters = {
        "message": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 280,
            "description": "The tweet message to post (max 280 characters)"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Twitter/X.com login credentials"
        },
        "wait_for_confirmation": {
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "Wait for tweet confirmation before completing"
        }
    }

    async def execute(self, message: str, credentials: dict[str, str],
                     wait_for_confirmation: bool = True) -> dict[str, Any]:
        """
        Execute the Twitter posting action.

        Args:
            message: The tweet message to post
            credentials: Twitter login credentials
            wait_for_confirmation: Whether to wait for confirmation

        Returns:
            Dict containing execution result with screenshots
        """
        logger.info("Starting Twitter post action",
                   message_length=len(message),
                   session_id=self.session_id)

        # Create Steel browser session
        session_id = await self.create_session(
            use_proxy=True,
            solve_captcha=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=60000  # 1 minute timeout
        )

        try:
            # Initialize browser session and Claude agent
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            # Execute the posting task with Claude
            task_description = self._build_task_description(message, credentials, wait_for_confirmation)
            context = {
                "action": "twitter_post",
                "message": message,
                "message_length": len(message),
                "wait_for_confirmation": wait_for_confirmation,
                "platform": "x.com"
            }

            result = await agent.execute_task(task_description, context)

            # Process and format the result
            return await self._process_result(result, message)

        except Exception as e:
            logger.error("Twitter post action failed", error=str(e), session_id=session_id)

            # Capture error screenshot
            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to post tweet: {str(e)}",
                error_code="TWITTER_POST_ERROR",
                details={
                    "message": message,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_task_description(self, message: str, credentials: dict[str, str],
                              wait_for_confirmation: bool) -> str:
        """Build detailed task description for Claude."""
        task = f"""
Complete a Twitter posting task:

1. NAVIGATE to x.com (Twitter)
2. LOGIN with the provided credentials
3. COMPOSE a new tweet with this exact message: "{message}"
4. POST the tweet
5. {"VERIFY the tweet was posted successfully" if wait_for_confirmation else "Complete after posting"}

IMPORTANT REQUIREMENTS:
- Use the exact message provided: "{message}"
- Ensure the message is within Twitter's 280 character limit
- Handle any captchas or verification steps
- If login fails, try alternative methods (email instead of username)
- Take screenshots at each major step
- Verify successful posting before completing

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

SUCCESS CRITERIA:
- Successfully logged into Twitter/X.com
- Tweet composed with exact message
- Tweet posted to timeline
- Confirmation of successful posting (if wait_for_confirmation=True)

Handle any errors gracefully and provide clear feedback on what went wrong.
"""
        return task.strip()

    async def _process_result(self, agent_result: dict[str, Any], original_message: str) -> dict[str, Any]:
        """Process Claude agent result into standardized action result."""

        # Extract key information
        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Build result data
        result_data = {
            "tweet_message": original_message,
            "message_length": len(original_message),
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0),
            "evidence": evidence
        }

        # Determine success/failure
        if status == "success":
            success_message = f"Successfully posted tweet: '{original_message[:50]}...'" if len(original_message) > 50 else f"Successfully posted tweet: '{original_message}'"
        else:
            success_message = f"Failed to post tweet: {claude_message}"

        # Get final screenshot
        final_screenshot = None
        if screenshots:
            final_screenshot = screenshots[-1].get("image_b64") if screenshots[-1] else None

        if not final_screenshot:
            # Try to capture a fresh screenshot
            final_screenshot = await self.capture_screenshot()

        return {
            "status": status,
            "message": success_message,
            "data": result_data,
            "screenshot": final_screenshot,
            "timestamp": time.time(),
            "execution_details": {
                "screenshots_captured": len(screenshots),
                "claude_response": claude_message,
                "session_id": self.session_id
            }
        }


class TwitterReplyAction(BaseAction):
    """Reply to a tweet on Twitter/X.com using browser automation."""

    # Action metadata
    name = "Reply to Twitter Post"
    description = "Reply to a specific tweet on Twitter"
    category = "social_media"
    tags = ["twitter", "x", "social", "reply", "engagement"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 60
    estimated_duration_seconds = 35
    success_rate_threshold = 0.80

    # Parameter schema
    parameters = {
        "tweet_url": {
            "type": "string",
            "required": True,
            "description": "URL of the tweet to reply to"
        },
        "reply_message": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 280,
            "description": "The reply message (max 280 characters)"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Twitter/X.com login credentials"
        }
    }

    async def execute(self, tweet_url: str, reply_message: str,
                     credentials: dict[str, str]) -> dict[str, Any]:
        """
        Execute the Twitter reply action.

        Args:
            tweet_url: URL of the tweet to reply to
            reply_message: The reply message to post
            credentials: Twitter login credentials

        Returns:
            Dict containing execution result with screenshots
        """
        logger.info("Starting Twitter reply action",
                   tweet_url=tweet_url,
                   reply_length=len(reply_message),
                   session_id=self.session_id)

        # Validate tweet URL
        if not self._is_valid_tweet_url(tweet_url):
            raise ActionValidationError(
                "Invalid Twitter URL provided",
                parameter="tweet_url"
            )

        # Create Steel browser session
        session_id = await self.create_session(
            use_proxy=True,
            solve_captcha=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=60000
        )

        try:
            # Initialize browser session and Claude agent
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            # Execute the reply task
            task_description = self._build_reply_task_description(
                tweet_url, reply_message, credentials
            )
            context = {
                "action": "twitter_reply",
                "tweet_url": tweet_url,
                "reply_message": reply_message,
                "reply_length": len(reply_message),
                "platform": "x.com"
            }

            result = await agent.execute_task(task_description, context)

            # Process and format the result
            return await self._process_reply_result(result, tweet_url, reply_message)

        except Exception as e:
            logger.error("Twitter reply action failed", error=str(e), session_id=session_id)

            # Capture error screenshot
            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to reply to tweet: {str(e)}",
                error_code="TWITTER_REPLY_ERROR",
                details={
                    "tweet_url": tweet_url,
                    "reply_message": reply_message,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _is_valid_tweet_url(self, url: str) -> bool:
        """Validate that URL is a valid Twitter/X.com tweet URL."""
        valid_patterns = [
            "twitter.com/",
            "x.com/",
            "/status/"
        ]

        url_lower = url.lower()
        return any(pattern in url_lower for pattern in valid_patterns)

    def _build_reply_task_description(self, tweet_url: str, reply_message: str,
                                    credentials: dict[str, str]) -> str:
        """Build detailed task description for Claude reply action."""
        task = f"""
Complete a Twitter reply task:

1. NAVIGATE to the tweet URL: {tweet_url}
2. LOGIN to Twitter/X.com with provided credentials (if not already logged in)
3. LOCATE the reply button for the specific tweet
4. CLICK the reply button to open the reply composer
5. COMPOSE the reply with this exact message: "{reply_message}"
6. POST the reply
7. VERIFY the reply was posted successfully

IMPORTANT REQUIREMENTS:
- Navigate directly to the tweet URL: {tweet_url}
- Use the exact reply message: "{reply_message}"
- Ensure the reply is posted to the correct tweet
- Handle any captchas or verification steps
- Take screenshots showing the original tweet and your reply
- Confirm successful posting

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

SUCCESS CRITERIA:
- Successfully navigated to the specific tweet
- Logged into Twitter/X.com (if needed)
- Reply composer opened for the correct tweet
- Reply message posted successfully
- Confirmation that reply appears under the original tweet

Handle any errors gracefully and provide clear feedback.
"""
        return task.strip()

    async def _process_reply_result(self, agent_result: dict[str, Any],
                                  tweet_url: str, reply_message: str) -> dict[str, Any]:
        """Process Claude agent result for reply action."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Build result data
        result_data = {
            "original_tweet_url": tweet_url,
            "reply_message": reply_message,
            "reply_length": len(reply_message),
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0),
            "evidence": evidence
        }

        # Determine success message
        if status == "success":
            success_message = f"Successfully replied to tweet with: '{reply_message[:50]}...'" if len(reply_message) > 50 else f"Successfully replied to tweet with: '{reply_message}'"
        else:
            success_message = f"Failed to reply to tweet: {claude_message}"

        # Get final screenshot
        final_screenshot = None
        if screenshots:
            final_screenshot = screenshots[-1].get("image_b64") if screenshots[-1] else None

        if not final_screenshot:
            final_screenshot = await self.capture_screenshot()

        return {
            "status": status,
            "message": success_message,
            "data": result_data,
            "screenshot": final_screenshot,
            "timestamp": time.time(),
            "execution_details": {
                "screenshots_captured": len(screenshots),
                "claude_response": claude_message,
                "session_id": self.session_id
            }
        }
