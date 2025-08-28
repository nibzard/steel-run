"""Website interaction actions for screenshots, scraping, and automation."""

import time
from typing import Any

import structlog

from ..agent.executor import BrowserSession, ClaudeAgent
from .base import ActionExecutionError, ActionValidationError, BaseAction

logger = structlog.get_logger(__name__)


class WebsiteScreenshotAction(BaseAction):
    """Take a screenshot of any website."""

    name = "Website Screenshot"
    description = "Capture a screenshot of any webpage"
    category = "website"
    tags = ["screenshot", "webpage", "capture"]

    parameters = {
        "url": {
            "type": "string",
            "required": True,
            "description": "URL of the webpage to screenshot",
            "min_length": 1,
        },
        "full_page": {
            "type": "boolean",
            "required": False,
            "description": "Capture full page or just viewport",
        },
        "delay": {
            "type": "integer",
            "required": False,
            "min_value": 0,
            "max_value": 30000,
            "description": "Wait time in milliseconds before capturing",
        },
        "width": {
            "type": "integer",
            "required": False,
            "min_value": 320,
            "max_value": 1920,
            "description": "Browser viewport width in pixels",
        },
        "height": {
            "type": "integer",
            "required": False,
            "min_value": 240,
            "max_value": 1080,
            "description": "Browser viewport height in pixels",
        }
    }

    timeout_seconds = 30
    estimated_duration_seconds = 5

    async def execute(self, **params) -> dict[str, Any]:
        """Execute website screenshot capture."""
        url = params["url"]
        full_page = params.get("full_page", False)
        delay = params.get("delay", 2000)  # Default 2 second delay
        width = params.get("width", 1280)
        height = params.get("height", 720)

        # Create browser session with specific dimensions
        session_options = {
            "dimensions": {"width": width, "height": height},
            "use_proxy": True,
            "block_ads": True,
        }

        session_id = await self.create_session(**session_options)

        try:
            # Initialize browser session and Claude agent
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            # Execute the screenshot task
            task_description = self._build_screenshot_task_description(
                url, full_page, delay, width, height
            )
            context = {
                "action": "website_screenshot",
                "url": url,
                "full_page": full_page,
                "delay": delay,
                "dimensions": {"width": width, "height": height}
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_screenshot_result(result, url, full_page, width, height)

        except Exception as e:
            raise ActionExecutionError(
                f"Failed to capture screenshot from {url}: {str(e)}",
                error_code="SCREENSHOT_ERROR"
            )


class WebsiteContentAction(BaseAction):
    """Extract text content from any website."""

    name = "Website Content"
    description = "Extract text content and basic information from any webpage"
    category = "website"
    tags = ["scraping", "content", "text", "extraction"]

    parameters = {
        "url": {
            "type": "string",
            "required": True,
            "description": "URL of the webpage to extract content from",
            "min_length": 1,
        },
        "format": {
            "type": "string",
            "required": False,
            "description": "Output format: 'text', 'markdown', or 'html'",
        },
        "delay": {
            "type": "integer",
            "required": False,
            "min_value": 0,
            "max_value": 30000,
            "description": "Wait time in milliseconds before extracting",
        },
        "include_links": {
            "type": "boolean",
            "required": False,
            "description": "Include links in the extracted content",
        },
    }

    timeout_seconds = 45
    estimated_duration_seconds = 8

    async def execute(self, **params) -> dict[str, Any]:
        """Execute website content extraction."""
        url = params["url"]
        output_format = params.get("format", "text")
        delay = params.get("delay", 3000)  # Default 3 second delay
        include_links = params.get("include_links", False)

        session_id = await self.create_session(
            use_proxy=True,
            block_ads=True,
            stealth_config={"humanize_interactions": False}  # Faster for scraping
        )

        try:
            # Initialize browser session and Claude agent
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            # Execute the content extraction task
            task_description = self._build_content_task_description(
                url, output_format, delay, include_links
            )
            context = {
                "action": "website_content",
                "url": url,
                "format": output_format,
                "delay": delay,
                "include_links": include_links
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_content_result(result, url, output_format, include_links)

        except Exception as e:
            # Capture error screenshot
            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to extract content from {url}: {str(e)}",
                error_code="CONTENT_EXTRACTION_ERROR",
                details={
                    "url": url,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_screenshot_task_description(self, url: str, full_page: bool,
                                         delay: int, width: int, height: int) -> str:
        """Build task description for screenshot capture."""

        task = f"""
Complete a website screenshot capture task:

1. NAVIGATE to the webpage: {url}
2. WAIT for complete page load and any dynamic content
3. WAIT an additional {delay}ms for any animations or lazy loading
4. CAPTURE a {'full page' if full_page else 'viewport'} screenshot
5. VERIFY the screenshot captured successfully

VIEWPORT SETTINGS:
- Width: {width}px
- Height: {height}px
- Full page capture: {full_page}

REQUIREMENTS:
- Navigate to exact URL: {url}
- Allow page to fully load before capturing
- Handle any cookie banners or popups gracefully
- Ensure screenshot quality and completeness
- Capture {'entire page content' if full_page else 'visible viewport area'}

SUCCESS CRITERIA:
- Successfully navigated to the webpage
- Page loaded completely with all resources
- Screenshot captured with good quality
- No major errors or missing content

ERROR HANDLING:
- Handle network timeouts gracefully
- Deal with certificate warnings if present
- Skip or dismiss intrusive popups
- Report any accessibility issues encountered
"""
        return task.strip()

    def _build_content_task_description(self, url: str, output_format: str,
                                       delay: int, include_links: bool) -> str:
        """Build task description for content extraction."""

        task = f"""
Complete a website content extraction task:

1. NAVIGATE to the webpage: {url}
2. WAIT for complete page load and dynamic content to render
3. WAIT an additional {delay}ms for any lazy-loaded content
4. EXTRACT text content from the page:
   - Main article/content text
   - Headings and structure
   - {'Include all links and their URLs' if include_links else 'Text only, no links'}
   - Clean up navigation, ads, and sidebar content
5. FORMAT the extracted content as {output_format}
6. TAKE screenshots showing the content extraction process

URL: {url}
OUTPUT FORMAT: {output_format}
INCLUDE LINKS: {include_links}

CONTENT EXTRACTION REQUIREMENTS:
- Focus on main content, skip navigation and ads
- Preserve text structure and hierarchy
- Extract headings, paragraphs, lists properly
- {'Capture link text and URLs for all links' if include_links else 'Extract clean text without link URLs'}
- Handle different content types (articles, blogs, documentation)
- Clean and format output appropriately

FORMATTING:
{f'- Convert to clean {output_format} format' if output_format != 'text' else '- Extract clean, readable text'}
{'- Preserve heading levels and structure' if output_format != 'text' else '- Remove formatting, keep structure'}
{'- Maintain readability and formatting' if output_format != 'text' else '- Focus on content readability'}
{'- Include metadata like title, author, date if available' if output_format != 'text' else ''}

SUCCESS CRITERIA:
- Successfully navigated and loaded the webpage
- Extracted main content accurately
- Properly formatted output as {output_format}
- {'Links extracted with text and URLs' if include_links else 'Clean text extraction completed'}
- Screenshots document the extraction process

ERROR HANDLING:
- Handle pages that require JavaScript
- Deal with content behind paywalls gracefully
- Skip or note unavailable content sections
- Handle different page layouts and structures
"""
        return task.strip()

    async def _process_screenshot_result(self, agent_result: dict[str, Any],
                                       url: str, full_page: bool, width: int, height: int) -> dict[str, Any]:
        """Process Claude agent result for screenshot capture."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "url": url,
            "full_page": full_page,
            "dimensions": {"width": width, "height": height},
            "final_url": agent_result.get("final_url", url),
            "page_title": evidence.get("page_title", "Unknown"),
            "screenshot_timestamp": time.time(),
            "page_load_time": evidence.get("page_load_time"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            success_message = f"Screenshot captured from {url}"
        else:
            success_message = f"Failed to capture screenshot: {claude_message}"

        # Get screenshot from agent result
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

    async def _process_content_result(self, agent_result: dict[str, Any], url: str,
                                    output_format: str, include_links: bool) -> dict[str, Any]:
        """Process Claude agent result for content extraction."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Extract content information from evidence
        extracted_content = evidence.get("content", "")
        extracted_links = evidence.get("links", []) if include_links else []

        result_data = {
            "url": url,
            "format": output_format,
            "content": extracted_content,
            "links": extracted_links,
            "word_count": len(extracted_content.split()) if extracted_content else 0,
            "character_count": len(extracted_content) if extracted_content else 0,
            "link_count": len(extracted_links),
            "final_url": agent_result.get("final_url", url),
            "page_title": evidence.get("page_title", "Unknown"),
            "extraction_timestamp": time.time(),
            "page_load_time": evidence.get("page_load_time"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            success_message = f"Content extracted from {url} ({result_data['word_count']} words)"
        else:
            success_message = f"Failed to extract content: {claude_message}"

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


class WebsiteFormFillerAction(BaseAction):
    """Fill and submit forms on websites using browser automation."""

    # Action metadata
    name = "Website Form Filler"
    description = "Fill out and submit forms on any website with specified data"
    category = "website"
    tags = ["form", "automation", "filling", "submission", "input"]

    # Performance settings
    timeout_seconds = 120  # Forms can be complex
    estimated_duration_seconds = 45
    success_rate_threshold = 0.75

    # Parameter schema
    parameters = {
        "url": {
            "type": "string",
            "required": True,
            "description": "URL of the webpage containing the form",
            "min_length": 1,
        },
        "form_data": {
            "type": "object",
            "required": True,
            "description": "Key-value pairs of form field names/IDs and their values"
        },
        "submit_form": {
            "type": "boolean",
            "required": False,
            "description": "Whether to submit the form after filling it"
        },
        "form_selector": {
            "type": "string",
            "required": False,
            "description": "CSS selector for the specific form (if multiple forms on page)"
        },
        "wait_after_submit": {
            "type": "integer",
            "required": False,
            "min_value": 0,
            "max_value": 30000,
            "description": "Time to wait after form submission in milliseconds"
        }
    }

    async def execute(self, url: str, form_data: dict[str, Any],
                     submit_form: bool = True, form_selector: str | None = None,
                     wait_after_submit: int = 3000) -> dict[str, Any]:
        """
        Execute form filling and submission.

        Args:
            url: URL containing the form
            form_data: Dictionary of field names/values
            submit_form: Whether to submit after filling
            form_selector: Optional form selector
            wait_after_submit: Wait time after submission

        Returns:
            Dict containing form filling results
        """
        if not form_data:
            raise ActionValidationError(
                "form_data cannot be empty",
                parameter="form_data"
            )

        logger.info("Starting website form filling action",
                   url=url,
                   field_count=len(form_data),
                   submit=submit_form,
                   session_id=self.session_id)

        # Create Steel browser session
        session_id = await self.create_session(
            use_proxy=True,
            block_ads=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=120000
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_form_task_description(
                url, form_data, submit_form, form_selector, wait_after_submit
            )
            context = {
                "action": "website_form_filler",
                "url": url,
                "form_data": form_data,
                "submit_form": submit_form,
                "form_selector": form_selector
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_form_result(result, url, form_data, submit_form)

        except Exception as e:
            logger.error("Website form filling action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to fill website form: {str(e)}",
                error_code="FORM_FILLING_ERROR",
                details={
                    "url": url,
                    "form_data_keys": list(form_data.keys()),
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_form_task_description(self, url: str, form_data: dict[str, Any],
                                   submit_form: bool, form_selector: str | None,
                                   wait_after_submit: int) -> str:
        """Build task description for form filling."""

        # Sanitize form data for display (hide sensitive values)
        display_form_data = {}
        for key, value in form_data.items():
            if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'token', 'key']):
                display_form_data[key] = "[HIDDEN]"
            else:
                display_form_data[key] = value

        task = f"""
Complete a website form filling task:

1. NAVIGATE to the webpage: {url}
2. WAIT for complete page load and identify the form
3. {"LOCATE the specific form using selector: " + form_selector if form_selector else "IDENTIFY the main form on the page"}
4. FILL OUT the form fields with provided data:

FORM DATA TO FILL:
{json.dumps(display_form_data, indent=2)}

5. VERIFY each field is filled correctly
6. {"SUBMIT the form and wait for response" if submit_form else "DO NOT submit - only fill the fields"}
{f"7. WAIT {wait_after_submit}ms after submission for page to process" if submit_form else ""}
8. TAKE screenshots showing the filled form {"and submission result" if submit_form else ""}

FORM FILLING REQUIREMENTS:
- Navigate to exact URL: {url}
- Identify form fields by name, id, placeholder, or label text
- Handle different input types (text, email, select, checkbox, radio, etc.)
- Fill fields in logical order
- Verify each field accepts the input correctly
- Handle any validation errors or required field warnings
- {"Submit the form using the submit button or Enter key" if submit_form else "Leave form filled but unsubmitted"}

FIELD MATCHING STRATEGY:
- Try field names first, then IDs, then other attributes
- Handle case-insensitive matching for field identification
- Look for labels and placeholder text if direct matching fails
- Handle complex form layouts and nested elements

SUCCESS CRITERIA:
- Successfully navigated to the webpage
- Located and identified the correct form
- All specified fields filled with correct values
- No validation errors or missing required fields
- {"Form submitted successfully with confirmation" if submit_form else "Form filled completely without submission"}
- Clear screenshots documenting the process

ERROR HANDLING:
- Handle missing form fields gracefully (note which fields couldn't be found)
- Deal with form validation errors appropriately
- Handle different form layouts and structures
- Report any fields that couldn't be filled and why
- Handle submission errors if they occur

SECURITY CONSIDERATIONS:
- Be careful with sensitive form data
- Don't leave sensitive information visible in screenshots
- Handle authentication forms appropriately
- Respect form rate limiting and security measures
"""

        return task.strip()

    async def _process_form_result(self, agent_result: dict[str, Any], url: str,
                                 form_data: dict[str, Any], submit_form: bool) -> dict[str, Any]:
        """Process Claude agent result for form filling."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "url": url,
            "fields_attempted": len(form_data),
            "fields_filled": evidence.get("fields_filled", 0),
            "fields_failed": evidence.get("fields_failed", []),
            "form_submitted": evidence.get("form_submitted", False) if submit_form else False,
            "submission_result": evidence.get("submission_result") if submit_form else None,
            "validation_errors": evidence.get("validation_errors", []),
            "final_url": agent_result.get("final_url", url),
            "processing_time": evidence.get("processing_time"),
            "timestamp": time.time(),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            filled_count = result_data["fields_filled"]
            total_count = result_data["fields_attempted"]
            base_message = f"Successfully filled {filled_count}/{total_count} form fields"

            if submit_form and result_data["form_submitted"]:
                success_message = base_message + " and submitted form"
            elif submit_form and not result_data["form_submitted"]:
                success_message = base_message + " but failed to submit form"
            else:
                success_message = base_message
        else:
            success_message = f"Failed to fill form: {claude_message}"

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
