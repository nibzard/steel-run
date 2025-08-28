"""Gmail automation actions using Steel and Claude Computer Use."""

import re
import time
from typing import Any

import structlog

from ..agent.executor import BrowserSession, ClaudeAgent
from .base import ActionExecutionError, ActionValidationError, BaseAction

logger = structlog.get_logger(__name__)


class GmailUnreadCountAction(BaseAction):
    """Check unread email count in Gmail."""

    # Action metadata
    name = "Gmail Unread Count"
    description = "Check the number of unread emails in Gmail inbox"
    category = "email"
    tags = ["gmail", "email", "unread", "count", "notification"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 60
    estimated_duration_seconds = 20
    success_rate_threshold = 0.85

    # Parameter schema
    parameters = {
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Gmail login credentials"
        },
        "include_categories": {
            "type": "boolean",
            "required": False,
            "description": "Include count by categories (Primary, Social, Promotions, etc.)"
        },
        "check_labels": {
            "type": "array",
            "required": False,
            "items": {"type": "string"},
            "description": "Specific labels to check for unread count"
        }
    }

    async def execute(self, credentials: dict[str, str],
                     include_categories: bool = False,
                     check_labels: list[str] | None = None) -> dict[str, Any]:
        """
        Execute Gmail unread count check.

        Args:
            credentials: Gmail login credentials
            include_categories: Include category-based counts
            check_labels: Specific labels to check

        Returns:
            Dict containing unread email counts
        """
        if check_labels is None:
            check_labels = []

        logger.info("Starting Gmail unread count action",
                   include_categories=include_categories,
                   check_labels=check_labels,
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
            api_timeout=60000,
            block_ads=False  # Gmail may have issues with ad blockers
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_unread_count_task_description(
                credentials, include_categories, check_labels
            )
            context = {
                "action": "gmail_unread_count",
                "include_categories": include_categories,
                "check_labels": check_labels,
                "platform": "gmail.com"
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_unread_count_result(result, include_categories, check_labels)

        except Exception as e:
            logger.error("Gmail unread count action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to check Gmail unread count: {str(e)}",
                error_code="GMAIL_UNREAD_COUNT_ERROR",
                details={
                    "include_categories": include_categories,
                    "check_labels": check_labels,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_unread_count_task_description(self, credentials: dict[str, str],
                                           include_categories: bool, check_labels: list[str]) -> str:
        """Build task description for Gmail unread count check."""

        labels_text = ""
        if check_labels:
            labels_text = f"""
SPECIFIC LABELS TO CHECK:
{chr(10).join(f"- {label}" for label in check_labels)}
"""

        task = f"""
Complete a Gmail unread email count check:

1. NAVIGATE to Gmail.com
2. LOGIN with provided credentials:
   - Handle 2FA if prompted
   - Manage any security challenges
3. WAIT for Gmail interface to load completely
4. CHECK unread email counts:

MAIN INBOX COUNT:
- Identify total unread emails in main inbox
- Note the exact number displayed

{"CATEGORY COUNTS (if include_categories=True):" if include_categories else ""}
{"""- Primary tab unread count
- Social tab unread count
- Promotions tab unread count
- Updates tab unread count
- Forums tab unread count
- Any other visible category tabs""" if include_categories else ""}

{labels_text}

5. EXTRACT additional email information:
   - Recent unread email senders and subjects (first few)
   - Any high-priority or starred unread emails
   - Total inbox size if visible
6. TAKE screenshots showing the Gmail interface and counts
7. COMPILE all count information into structured format

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

GMAIL INTERFACE REQUIREMENTS:
- Navigate to standard Gmail web interface
- Handle Gmail's dynamic loading and updates
- Identify unread count indicators accurately
- Handle different Gmail themes and layouts
- Extract exact numerical counts, not approximations
- {"Navigate between category tabs to get individual counts" if include_categories else ""}
- {"Check specific labels in the sidebar for unread counts" if check_labels else ""}

SUCCESS CRITERIA:
- Successfully logged into Gmail
- Gmail interface loaded completely
- Main inbox unread count identified
- {"Category-specific counts extracted" if include_categories else ""}
- {"Label-specific counts checked" if check_labels else ""}
- Additional context information collected
- Clear screenshots showing the counts

ERROR HANDLING:
- Handle Gmail login variations and security measures
- Deal with different Gmail interface versions
- Manage inbox organization variations (tabs vs labels)
- Handle empty inboxes appropriately
- Report any access or loading issues
- Adapt to Gmail UI changes and A/B tests

PRIVACY AND SECURITY:
- Don't read email content, only count information
- Handle sensitive account information appropriately
- Respect Gmail's access patterns and rate limits
- Don't leave the account in an unsecure state
- Follow appropriate logout procedures if needed
"""

        return task.strip()

    async def _process_unread_count_result(self, agent_result: dict[str, Any],
                                         include_categories: bool, check_labels: list[str]) -> dict[str, Any]:
        """Process Claude agent result for unread count check."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "check_timestamp": time.time(),

            # Main counts
            "total_unread": evidence.get("total_unread", 0),
            "inbox_unread": evidence.get("inbox_unread", 0),

            # Category counts (if requested)
            "category_counts": evidence.get("category_counts", {}) if include_categories else {},

            # Label counts (if requested)
            "label_counts": evidence.get("label_counts", {}) if check_labels else {},

            # Additional information
            "recent_unread": evidence.get("recent_unread", []),
            "high_priority_unread": evidence.get("high_priority_unread", 0),
            "starred_unread": evidence.get("starred_unread", 0),
            "total_emails": evidence.get("total_emails"),
            "storage_used": evidence.get("storage_used"),

            # Gmail account info
            "account_info": evidence.get("account_info", {}),
            "gmail_version": evidence.get("gmail_version"),

            # Metadata
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            unread_count = result_data["total_unread"]
            success_message = f"Found {unread_count} unread email{'s' if unread_count != 1 else ''} in Gmail"

            if include_categories and result_data["category_counts"]:
                category_summary = ", ".join([
                    f"{cat}: {count}" for cat, count in result_data["category_counts"].items() if count > 0
                ])
                if category_summary:
                    success_message += f" ({category_summary})"
        else:
            success_message = f"Failed to check Gmail unread count: {claude_message}"

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


class GmailReadEmailsAction(BaseAction):
    """Read and parse emails from Gmail with filtering options."""

    # Action metadata
    name = "Gmail Read Emails"
    description = "Read and parse emails from Gmail inbox with filtering and search options"
    category = "email"
    tags = ["gmail", "email", "read", "parse", "filter", "search"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 120  # Reading emails can take time
    estimated_duration_seconds = 60
    success_rate_threshold = 0.80

    # Parameter schema
    parameters = {
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Gmail login credentials"
        },
        "search_query": {
            "type": "string",
            "required": False,
            "description": "Gmail search query to filter emails"
        },
        "max_emails": {
            "type": "integer",
            "required": False,
            "min_value": 1,
            "max_value": 50,
            "description": "Maximum number of emails to read (default 10)"
        },
        "only_unread": {
            "type": "boolean",
            "required": False,
            "description": "Only read unread emails"
        },
        "include_attachments": {
            "type": "boolean",
            "required": False,
            "description": "Include information about email attachments"
        },
        "mark_as_read": {
            "type": "boolean",
            "required": False,
            "description": "Mark emails as read after processing"
        }
    }

    async def execute(self, credentials: dict[str, str],
                     search_query: str | None = None,
                     max_emails: int = 10, only_unread: bool = True,
                     include_attachments: bool = False,
                     mark_as_read: bool = False) -> dict[str, Any]:
        """
        Execute Gmail email reading and parsing.

        Args:
            credentials: Gmail login credentials
            search_query: Search query for filtering
            max_emails: Maximum emails to read
            only_unread: Only read unread emails
            include_attachments: Include attachment info
            mark_as_read: Mark as read after processing

        Returns:
            Dict containing parsed email data
        """
        if max_emails > 50:
            raise ActionValidationError(
                "max_emails cannot exceed 50",
                parameter="max_emails"
            )

        logger.info("Starting Gmail read emails action",
                   search_query=search_query,
                   max_emails=max_emails,
                   only_unread=only_unread,
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
            api_timeout=120000,
            block_ads=False
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_read_emails_task_description(
                credentials, search_query, max_emails, only_unread,
                include_attachments, mark_as_read
            )
            context = {
                "action": "gmail_read_emails",
                "search_query": search_query,
                "max_emails": max_emails,
                "only_unread": only_unread,
                "include_attachments": include_attachments,
                "mark_as_read": mark_as_read
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_read_emails_result(result, search_query, max_emails, only_unread)

        except Exception as e:
            logger.error("Gmail read emails action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to read Gmail emails: {str(e)}",
                error_code="GMAIL_READ_EMAILS_ERROR",
                details={
                    "search_query": search_query,
                    "max_emails": max_emails,
                    "only_unread": only_unread,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_read_emails_task_description(self, credentials: dict[str, str],
                                          search_query: str | None, max_emails: int,
                                          only_unread: bool, include_attachments: bool,
                                          mark_as_read: bool) -> str:
        """Build task description for reading Gmail emails."""

        search_text = ""
        if search_query:
            search_text = f"""
SEARCH AND FILTER EMAILS:
- Use Gmail search query: "{search_query}"
- Apply the search to filter relevant emails
- Ensure search results are loaded completely
"""

        task = f"""
Complete a Gmail email reading and parsing task:

1. NAVIGATE to Gmail.com
2. LOGIN with provided credentials:
   - Handle 2FA and security challenges
3. WAIT for Gmail interface to load completely

{search_text}4. {"FILTER to unread emails only" if only_unread else "INCLUDE both read and unread emails"}

5. READ AND PARSE EMAILS (up to {max_emails} emails):

FOR EACH EMAIL, EXTRACT:
- Subject line
- Sender name and email address
- Date and time sent
- Email body content (full text)
- Read/unread status
- Priority/importance markers
- Labels and categories
{"- Attachment information (names, types, sizes)" if include_attachments else ""}
- Thread/conversation information
- Gmail message ID if available

6. {"OPEN each email to read full content" if max_emails <= 20 else "Extract available information from inbox view, opening emails as needed for full content"}
7. {"MARK emails as read after processing" if mark_as_read else "LEAVE read status unchanged"}
8. TAKE screenshots showing the email list and content
9. COMPILE all email data into structured format

READING PARAMETERS:
{"- Search Query: '" + search_query + "'" if search_query else ""}
- Max Emails: {max_emails}
- Only Unread: {only_unread}
- Include Attachments: {include_attachments}
- Mark as Read: {mark_as_read}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

EMAIL EXTRACTION REQUIREMENTS:
- Extract complete and accurate email information
- Handle Gmail's conversation threading appropriately
- Preserve email formatting and structure where relevant
- Handle HTML and plain text emails correctly
- Extract exact timestamps and sender information
- {"Note attachment details without downloading files" if include_attachments else ""}
- Handle long emails with expansion/truncation
- Respect Gmail's interface patterns and loading

GMAIL NAVIGATION:
- Use Gmail's standard web interface
- Handle inbox organization (categories, labels)
- Manage email list pagination if needed
- Click into emails for full content reading
- Handle Gmail's keyboard shortcuts and UI
- Navigate conversation threads appropriately
- {"Apply read status changes carefully" if mark_as_read else ""}

SUCCESS CRITERIA:
- Successfully logged into Gmail
- {"Applied search query and found relevant emails" if search_query else "Accessed inbox successfully"}
- Read up to {max_emails} emails as specified
- Extracted complete email information
- {"Processed attachment information" if include_attachments else ""}
- {"Marked emails as read appropriately" if mark_as_read else ""}
- Clear screenshots document the process

ERROR HANDLING:
- Handle emails with loading issues
- Manage protected or restricted content
- Deal with very long email threads
- Handle attachment processing errors
- Report any emails that couldn't be read
- Adapt to Gmail interface variations

PRIVACY AND SECURITY:
- Handle sensitive email content appropriately
- Don't download or save attachments permanently
- Respect email privacy and security
- Handle business vs personal email content
- Follow appropriate data handling practices
"""

        return task.strip()

    async def _process_read_emails_result(self, agent_result: dict[str, Any],
                                        search_query: str | None, max_emails: int,
                                        only_unread: bool) -> dict[str, Any]:
        """Process Claude agent result for email reading."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Extract email data
        emails = evidence.get("emails", [])

        result_data = {
            "search_query": search_query,
            "max_emails_requested": max_emails,
            "only_unread": only_unread,
            "emails_found": len(emails),
            "read_timestamp": time.time(),

            # Email data
            "emails": emails,

            # Processing metadata
            "processing_stats": {
                "emails_processed": evidence.get("emails_processed", 0),
                "unread_count": evidence.get("unread_count", 0),
                "read_count": evidence.get("read_count", 0),
                "failed_to_read": evidence.get("failed_to_read", []),
                "attachments_found": evidence.get("total_attachments", 0),
                "threads_processed": evidence.get("threads_processed", 0)
            },

            # Gmail context
            "gmail_info": evidence.get("gmail_info", {}),
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            emails_count = result_data["emails_found"]
            success_message = f"Successfully read {emails_count} email{'s' if emails_count != 1 else ''}"

            if search_query:
                success_message += f" matching '{search_query}'"
            if only_unread:
                success_message += " (unread only)"
        else:
            success_message = f"Failed to read Gmail emails: {claude_message}"

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


class GmailSendEmailAction(BaseAction):
    """Compose and send emails through Gmail."""

    # Action metadata
    name = "Gmail Send Email"
    description = "Compose and send emails through Gmail with attachments and formatting"
    category = "email"
    tags = ["gmail", "email", "send", "compose", "communication"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 90
    estimated_duration_seconds = 30
    success_rate_threshold = 0.85

    # Parameter schema
    parameters = {
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Gmail login credentials"
        },
        "to": {
            "type": "array",
            "required": True,
            "items": {"type": "string"},
            "min_items": 1,
            "max_items": 20,
            "description": "Recipient email addresses"
        },
        "subject": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 200,
            "description": "Email subject line"
        },
        "body": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "description": "Email body content"
        },
        "cc": {
            "type": "array",
            "required": False,
            "items": {"type": "string"},
            "max_items": 20,
            "description": "CC recipient email addresses"
        },
        "bcc": {
            "type": "array",
            "required": False,
            "items": {"type": "string"},
            "max_items": 20,
            "description": "BCC recipient email addresses"
        },
        "formatting": {
            "type": "object",
            "required": False,
            "properties": {
                "bold_text": {"type": "array", "items": {"type": "string"}},
                "italic_text": {"type": "array", "items": {"type": "string"}},
                "links": {"type": "array", "items": {"type": "object"}}
            },
            "description": "Text formatting options"
        },
        "priority": {
            "type": "string",
            "required": False,
            "description": "Email priority: normal, high, low"
        }
    }

    async def execute(self, credentials: dict[str, str], to: list[str],
                     subject: str, body: str, cc: list[str] | None = None,
                     bcc: list[str] | None = None, formatting: dict | None = None,
                     priority: str = "normal") -> dict[str, Any]:
        """
        Execute Gmail email sending.

        Args:
            credentials: Gmail login credentials
            to: Recipient email addresses
            subject: Email subject
            body: Email body content
            cc: CC recipients
            bcc: BCC recipients
            formatting: Text formatting options
            priority: Email priority

        Returns:
            Dict containing email sending results
        """
        # Validate email addresses
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        for email in to:
            if not re.match(email_pattern, email):
                raise ActionValidationError(
                    f"Invalid email address in 'to' field: {email}",
                    parameter="to"
                )

        if cc:
            for email in cc:
                if not re.match(email_pattern, email):
                    raise ActionValidationError(
                        f"Invalid email address in 'cc' field: {email}",
                        parameter="cc"
                    )

        if bcc:
            for email in bcc:
                if not re.match(email_pattern, email):
                    raise ActionValidationError(
                        f"Invalid email address in 'bcc' field: {email}",
                        parameter="bcc"
                    )

        if priority not in ["normal", "high", "low"]:
            raise ActionValidationError(
                "Priority must be 'normal', 'high', or 'low'",
                parameter="priority"
            )

        if cc is None:
            cc = []
        if bcc is None:
            bcc = []
        if formatting is None:
            formatting = {}

        logger.info("Starting Gmail send email action",
                   recipients=len(to),
                   cc_count=len(cc),
                   bcc_count=len(bcc),
                   subject=subject[:50],
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
            api_timeout=90000,
            block_ads=False
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_send_email_task_description(
                credentials, to, subject, body, cc, bcc, formatting, priority
            )
            context = {
                "action": "gmail_send_email",
                "to": to,
                "subject": subject,
                "body": body,
                "cc": cc,
                "bcc": bcc,
                "formatting": formatting,
                "priority": priority
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_send_email_result(result, to, subject, body)

        except Exception as e:
            logger.error("Gmail send email action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to send Gmail email: {str(e)}",
                error_code="GMAIL_SEND_EMAIL_ERROR",
                details={
                    "to": to,
                    "subject": subject,
                    "body_length": len(body),
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_send_email_task_description(self, credentials: dict[str, str],
                                         to: list[str], subject: str, body: str,
                                         cc: list[str], bcc: list[str],
                                         formatting: dict, priority: str) -> str:
        """Build task description for sending email via Gmail."""

        recipients_text = f"""
TO: {', '.join(to)}
{"CC: " + ', '.join(cc) if cc else ""}
{"BCC: " + ', '.join(bcc) if bcc else ""}"""

        formatting_text = ""
        if formatting:
            if formatting.get("bold_text"):
                formatting_text += f"- Bold text: {', '.join(formatting['bold_text'])}\n"
            if formatting.get("italic_text"):
                formatting_text += f"- Italic text: {', '.join(formatting['italic_text'])}\n"
            if formatting.get("links"):
                formatting_text += f"- Links to format: {len(formatting['links'])} link(s)\n"

        task = f"""
Complete a Gmail email composition and sending task:

1. NAVIGATE to Gmail.com
2. LOGIN with provided credentials:
   - Handle 2FA and security challenges appropriately
3. WAIT for Gmail interface to load completely
4. CLICK "Compose" button to start new email
5. FILL IN email fields:

RECIPIENTS:
{recipients_text}

SUBJECT: {subject}

EMAIL BODY:
{body}

6. APPLY FORMATTING (if specified):
{formatting_text if formatting_text else "- Use standard formatting (no special formatting requested)"}

7. SET EMAIL PRIORITY: {priority.upper()}
8. REVIEW the composed email carefully
9. SEND the email by clicking "Send" button
10. VERIFY the email was sent successfully
11. TAKE screenshots showing composition and sending confirmation

EMAIL DETAILS:
- Recipients: {len(to)} TO, {len(cc)} CC, {len(bcc)} BCC
- Subject: "{subject}"
- Body length: {len(body)} characters
- Priority: {priority}
- Formatting: {"Yes" if formatting else "No"}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

GMAIL COMPOSITION REQUIREMENTS:
- Use Gmail's standard compose interface
- Fill all recipient fields accurately (TO, CC, BCC)
- Enter exact subject line: "{subject}"
- Include complete email body content
- {"Apply specified text formatting using Gmail's formatting tools" if formatting else "Use standard text formatting"}
- Set appropriate email priority level
- Handle Gmail's auto-save and draft functionality
- Verify all information before sending

FORMATTING APPLICATION:
{"- Use Gmail's rich text formatting toolbar" if formatting else ""}
{"- Apply bold formatting to specified text segments" if formatting.get("bold_text") else ""}
{"- Apply italic formatting to specified text segments" if formatting.get("italic_text") else ""}
{"- Add hyperlinks as specified" if formatting.get("links") else ""}
- Preserve email structure and readability
- Ensure formatting enhances rather than hinders readability

SUCCESS CRITERIA:
- Successfully logged into Gmail
- Composed email with all specified fields
- Applied all requested formatting correctly
- Set appropriate priority level
- {"Sent email to all recipients (" + str(len(to) + len(cc) + len(bcc)) + " total)" if cc or bcc else f"Sent email to {len(to)} recipient{'s' if len(to) > 1 else ''}"}
- Received confirmation of successful sending
- Clear screenshots document the process

ERROR HANDLING:
- Handle invalid or blocked email addresses
- Deal with Gmail's sending limits if encountered
- Manage attachment or formatting issues
- Handle network problems during sending
- Report any delivery warnings or errors
- Adapt to Gmail interface changes

COMPLIANCE AND BEST PRACTICES:
- Follow Gmail's terms of service
- Respect email etiquette and professional standards
- Handle sensitive content appropriately
- Verify recipient addresses before sending
- Ensure proper email formatting and structure
- Maintain appropriate sending frequency
"""

        return task.strip()

    async def _process_send_email_result(self, agent_result: dict[str, Any],
                                       to: list[str], subject: str, body: str) -> dict[str, Any]:
        """Process Claude agent result for email sending."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "recipients": to,
            "subject": subject,
            "body_length": len(body),
            "email_sent": evidence.get("email_sent", False),
            "message_id": evidence.get("message_id"),
            "send_timestamp": time.time(),
            "delivery_info": evidence.get("delivery_info", {}),
            "gmail_response": evidence.get("gmail_response", ""),
            "total_recipients": evidence.get("total_recipients", len(to)),
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success" and result_data["email_sent"]:
            recipient_count = result_data["total_recipients"]
            success_message = f"Successfully sent email '{subject}' to {recipient_count} recipient{'s' if recipient_count > 1 else ''}"
        elif status == "success" and not result_data["email_sent"]:
            success_message = "Email composed but not sent - " + result_data["gmail_response"]
        else:
            success_message = f"Failed to send email: {claude_message}"

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


class GmailSearchAction(BaseAction):
    """Search Gmail emails with advanced query support."""

    # Action metadata
    name = "Gmail Search"
    description = "Search Gmail emails using advanced search queries and filters"
    category = "email"
    tags = ["gmail", "search", "query", "filter", "find"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 90
    estimated_duration_seconds = 30
    success_rate_threshold = 0.85

    # Parameter schema
    parameters = {
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Gmail login credentials"
        },
        "search_query": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "description": "Gmail search query (supports advanced search operators)"
        },
        "max_results": {
            "type": "integer",
            "required": False,
            "min_value": 1,
            "max_value": 100,
            "description": "Maximum number of search results to return (default 20)"
        },
        "include_content": {
            "type": "boolean",
            "required": False,
            "description": "Include email content in results (slower but more detailed)"
        },
        "sort_by": {
            "type": "string",
            "required": False,
            "description": "Sort results by: date, relevance, sender"
        }
    }

    async def execute(self, credentials: dict[str, str], search_query: str,
                     max_results: int = 20, include_content: bool = False,
                     sort_by: str = "date") -> dict[str, Any]:
        """
        Execute Gmail search with advanced querying.

        Args:
            credentials: Gmail credentials
            search_query: Search query string
            max_results: Maximum results to return
            include_content: Include email content
            sort_by: Sort criteria

        Returns:
            Dict containing search results
        """
        if max_results > 100:
            raise ActionValidationError(
                "max_results cannot exceed 100",
                parameter="max_results"
            )

        valid_sort_options = ["date", "relevance", "sender"]
        if sort_by not in valid_sort_options:
            raise ActionValidationError(
                f"Invalid sort_by option. Must be one of: {', '.join(valid_sort_options)}",
                parameter="sort_by"
            )

        logger.info("Starting Gmail search action",
                   query=search_query,
                   max_results=max_results,
                   include_content=include_content,
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
            api_timeout=90000,
            block_ads=False
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_search_task_description(
                credentials, search_query, max_results, include_content, sort_by
            )
            context = {
                "action": "gmail_search",
                "search_query": search_query,
                "max_results": max_results,
                "include_content": include_content,
                "sort_by": sort_by
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_search_result(result, search_query, max_results, include_content)

        except Exception as e:
            logger.error("Gmail search action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to search Gmail: {str(e)}",
                error_code="GMAIL_SEARCH_ERROR",
                details={
                    "search_query": search_query,
                    "max_results": max_results,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_search_task_description(self, credentials: dict[str, str],
                                     search_query: str, max_results: int,
                                     include_content: bool, sort_by: str) -> str:
        """Build task description for Gmail search."""

        task = f"""
Complete a Gmail search task with advanced querying:

1. NAVIGATE to Gmail.com
2. LOGIN with provided credentials:
   - Handle 2FA and security challenges
3. WAIT for Gmail interface to load completely
4. PERFORM GMAIL SEARCH:
   - Enter search query in Gmail search box: "{search_query}"
   - Execute the search and wait for results
   - Handle Gmail's search suggestions and auto-complete

5. PROCESS SEARCH RESULTS (up to {max_results} results):

EXTRACT FOR EACH EMAIL:
- Subject line
- Sender name and email address
- Date and time
- Read/unread status
- Conversation/thread information
- Labels and categories
- Snippet/preview text
{"- Full email content (open emails to read complete content)" if include_content else ""}
- Attachment indicators
- Gmail message/conversation ID

6. SORT RESULTS by {sort_by.upper()} if different from default
7. {"OPEN individual emails to extract full content" if include_content else "EXTRACT available information from search results view"}
8. TAKE screenshots showing search interface and results
9. COMPILE all search results into structured format

SEARCH PARAMETERS:
- Query: "{search_query}"
- Max Results: {max_results}
- Include Content: {include_content}
- Sort By: {sort_by}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

GMAIL SEARCH REQUIREMENTS:
- Use Gmail's native search functionality
- Handle Gmail search operators (from:, to:, subject:, has:attachment, etc.)
- Process search results accurately and completely
- Handle different result types (individual emails vs conversations)
- Extract precise metadata for each result
- {"Navigate into emails for full content extraction" if include_content else "Focus on efficient metadata extraction"}
- Handle search pagination if results exceed one page
- Respect Gmail's search performance and limitations

ADVANCED SEARCH FEATURES:
- Support Gmail search operators in the query
- Handle date range searches appropriately
- Process label-based and category-based searches
- Manage attachment-based searches
- Handle sender/recipient specific searches
- Process subject line and content searches

SUCCESS CRITERIA:
- Successfully logged into Gmail
- Executed search with exact query: "{search_query}"
- Retrieved up to {max_results} relevant results
- Extracted complete metadata for each result
- {"Included full email content for all results" if include_content else "Included email previews and metadata"}
- Results sorted by {sort_by} criteria
- Clear screenshots document search process and results

ERROR HANDLING:
- Handle searches with no results gracefully
- Manage Gmail search limitations and errors
- Deal with protected or restricted content
- Handle search result loading issues
- Report any emails that couldn't be processed
- Adapt to Gmail search interface variations

PERFORMANCE OPTIMIZATION:
- {"Balance thoroughness with speed for content extraction" if include_content else "Optimize for fast metadata extraction"}
- Handle large search result sets efficiently
- Minimize unnecessary email opening and navigation
- Batch similar operations when possible
- Manage Gmail's rate limiting appropriately
"""

        return task.strip()

    async def _process_search_result(self, agent_result: dict[str, Any],
                                   search_query: str, max_results: int,
                                   include_content: bool) -> dict[str, Any]:
        """Process Claude agent result for Gmail search."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Extract search results
        search_results = evidence.get("search_results", [])
        search_metadata = evidence.get("search_metadata", {})

        result_data = {
            "search_query": search_query,
            "max_results_requested": max_results,
            "include_content": include_content,
            "results_found": len(search_results),
            "search_timestamp": time.time(),

            # Search results
            "search_results": search_results,

            # Search metadata
            "search_info": {
                "total_matches": search_metadata.get("total_matches", 0),
                "pages_searched": search_metadata.get("pages_searched", 1),
                "search_time_ms": search_metadata.get("search_time_ms", 0),
                "query_suggestions": search_metadata.get("query_suggestions", []),
                "applied_filters": search_metadata.get("applied_filters", [])
            },

            # Processing stats
            "processing_stats": {
                "emails_processed": evidence.get("emails_processed", 0),
                "content_extracted": evidence.get("content_extracted", 0),
                "failed_extractions": evidence.get("failed_extractions", []),
                "attachments_detected": evidence.get("attachments_detected", 0)
            },

            # Context
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            results_count = result_data["results_found"]
            total_matches = result_data["search_info"]["total_matches"]
            success_message = f"Found {results_count} result{'s' if results_count != 1 else ''} for '{search_query}'"

            if total_matches > results_count:
                success_message += f" (showing {results_count} of {total_matches} total matches)"

            if include_content:
                content_count = result_data["processing_stats"]["content_extracted"]
                success_message += f", extracted content from {content_count} email{'s' if content_count != 1 else ''}"
        else:
            success_message = f"Failed to search Gmail: {claude_message}"

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
