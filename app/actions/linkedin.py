"""LinkedIn automation actions using Steel and Claude Computer Use."""

import time
from typing import Any
from urllib.parse import urlparse

import structlog

from ..agent.executor import BrowserSession, ClaudeAgent
from .base import ActionExecutionError, ActionValidationError, BaseAction

logger = structlog.get_logger(__name__)


class LinkedInProfileExtractorAction(BaseAction):
    """Extract comprehensive profile data from LinkedIn profiles."""

    # Action metadata
    name = "LinkedIn Profile Extractor"
    description = "Extract detailed profile information from LinkedIn profiles"
    category = "professional"
    tags = ["linkedin", "profile", "extraction", "professional", "data"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 120  # LinkedIn can be slow and has complex layouts
    estimated_duration_seconds = 60
    success_rate_threshold = 0.70  # Lower due to LinkedIn's anti-bot measures

    # Parameter schema
    parameters = {
        "profile_url": {
            "type": "string",
            "required": True,
            "description": "LinkedIn profile URL to extract data from"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "LinkedIn login credentials"
        },
        "extract_details": {
            "type": "object",
            "required": False,
            "properties": {
                "basic_info": {"type": "boolean", "default": True},
                "experience": {"type": "boolean", "default": True},
                "education": {"type": "boolean", "default": True},
                "skills": {"type": "boolean", "default": True},
                "connections": {"type": "boolean", "default": False},
                "recommendations": {"type": "boolean", "default": False}
            },
            "description": "Specify which profile sections to extract"
        },
        "include_contact": {
            "type": "boolean",
            "required": False,
            "description": "Include contact information if available"
        }
    }

    async def execute(self, profile_url: str, credentials: dict[str, str],
                     extract_details: dict | None = None,
                     include_contact: bool = False) -> dict[str, Any]:
        """
        Execute LinkedIn profile data extraction.

        Args:
            profile_url: LinkedIn profile URL
            credentials: LinkedIn login credentials
            extract_details: Sections to extract
            include_contact: Include contact information

        Returns:
            Dict containing extracted profile data
        """
        if not self._is_valid_linkedin_url(profile_url):
            raise ActionValidationError(
                "Invalid LinkedIn profile URL provided",
                parameter="profile_url"
            )

        # Set default extraction details
        if extract_details is None:
            extract_details = {
                "basic_info": True,
                "experience": True,
                "education": True,
                "skills": True,
                "connections": False,
                "recommendations": False
            }

        logger.info("Starting LinkedIn profile extraction action",
                   url=profile_url,
                   extract_details=extract_details,
                   session_id=self.session_id)

        # Create Steel browser session optimized for LinkedIn
        session_id = await self.create_session(
            use_proxy=True,
            solve_captcha=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False,
                "random_user_agent": True
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=120000,
            block_ads=False  # LinkedIn may have issues with ad blockers
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_profile_extraction_task_description(
                profile_url, credentials, extract_details, include_contact
            )
            context = {
                "action": "linkedin_profile_extractor",
                "profile_url": profile_url,
                "extract_details": extract_details,
                "include_contact": include_contact,
                "platform": "linkedin.com"
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_profile_result(result, profile_url, extract_details)

        except Exception as e:
            logger.error("LinkedIn profile extraction action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to extract LinkedIn profile: {str(e)}",
                error_code="LINKEDIN_PROFILE_ERROR",
                details={
                    "profile_url": profile_url,
                    "extract_details": extract_details,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _is_valid_linkedin_url(self, url: str) -> bool:
        """Validate that URL is a valid LinkedIn profile URL."""
        try:
            parsed = urlparse(url.lower())
            valid_domains = ["linkedin.com", "www.linkedin.com"]

            if parsed.netloc not in valid_domains:
                return False

            # Check for profile URL patterns
            profile_patterns = ["/in/", "/pub/"]
            return any(pattern in parsed.path for pattern in profile_patterns)

        except Exception:
            return False

    def _build_profile_extraction_task_description(self, profile_url: str,
                                                  credentials: dict[str, str],
                                                  extract_details: dict,
                                                  include_contact: bool) -> str:
        """Build detailed task description for LinkedIn profile extraction."""

        sections_to_extract = []
        if extract_details.get("basic_info", True):
            sections_to_extract.append("- Basic information (name, headline, location, summary)")
        if extract_details.get("experience", True):
            sections_to_extract.append("- Work experience (positions, companies, dates, descriptions)")
        if extract_details.get("education", True):
            sections_to_extract.append("- Education (schools, degrees, dates)")
        if extract_details.get("skills", True):
            sections_to_extract.append("- Skills and endorsements")
        if extract_details.get("connections", False):
            sections_to_extract.append("- Connection count")
        if extract_details.get("recommendations", False):
            sections_to_extract.append("- Recommendations given/received")
        if include_contact:
            sections_to_extract.append("- Contact information (if accessible)")

        sections_text = "\n".join(sections_to_extract)

        task = f"""
Complete a LinkedIn profile data extraction task:

1. NAVIGATE to LinkedIn.com
2. LOGIN with provided credentials:
   - Handle any security challenges (captcha, 2FA, etc.)
   - Deal with login variations and updates
3. NAVIGATE to the target profile: {profile_url}
4. WAIT for profile to load completely
5. EXTRACT the following profile data:

{sections_text}

6. NAVIGATE through different sections as needed:
   - Scroll to load all content
   - Click "Show more" or expansion buttons where available
   - Handle LinkedIn's lazy loading of content
7. TAKE screenshots at each major section
8. COMPILE extracted data into structured format

PROFILE URL: {profile_url}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

DATA EXTRACTION REQUIREMENTS:
- Extract complete and accurate information from each section
- Handle LinkedIn's dynamic content loading
- Preserve formatting and structure where relevant
- Note any restricted or unavailable information
- Handle profile privacy settings gracefully
- Extract dates in consistent format (MM/YYYY)
- Capture company names, job titles, and descriptions accurately

LINKEDIN-SPECIFIC HANDLING:
- Respect LinkedIn's rate limiting and interaction patterns
- Handle premium vs. free account limitations
- Deal with "LinkedIn member" placeholder names appropriately
- Navigate LinkedIn's complex and changing UI structure
- Handle profile sections that may not be visible to all users
- Manage LinkedIn's anti-scraping measures

SUCCESS CRITERIA:
- Successfully logged into LinkedIn
- Navigated to the target profile
- Extracted all requested profile sections
- Data is complete and well-structured
- Screenshots document the extraction process
- No major sections missed or incomplete

ERROR HANDLING:
- Handle login failures and security challenges
- Deal with private or restricted profiles gracefully
- Manage network timeouts and page load issues
- Handle profiles with incomplete information
- Report any sections that couldn't be accessed
- Adapt to LinkedIn UI changes and variations

PRIVACY AND COMPLIANCE:
- Respect LinkedIn's terms of service
- Handle private information appropriately
- Don't attempt to extract restricted content
- Note any privacy limitations encountered
- Follow ethical data extraction practices
"""

        return task.strip()

    async def _process_profile_result(self, agent_result: dict[str, Any],
                                    profile_url: str, extract_details: dict) -> dict[str, Any]:
        """Process Claude agent result for LinkedIn profile extraction."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Structure the extracted profile data
        profile_data = {
            "profile_url": profile_url,
            "extraction_timestamp": time.time(),

            # Basic information
            "basic_info": evidence.get("basic_info", {}),

            # Professional information
            "current_position": evidence.get("current_position", {}),
            "experience": evidence.get("experience", []),
            "education": evidence.get("education", []),

            # Skills and endorsements
            "skills": evidence.get("skills", []),
            "endorsements": evidence.get("endorsements", {}),

            # Network information
            "connections_count": evidence.get("connections_count"),
            "mutual_connections": evidence.get("mutual_connections", []),

            # Additional information
            "recommendations": evidence.get("recommendations", []),
            "contact_info": evidence.get("contact_info", {}) if extract_details.get("include_contact") else {},
            "certifications": evidence.get("certifications", []),
            "languages": evidence.get("languages", []),
            "volunteer_experience": evidence.get("volunteer_experience", []),

            # Profile metadata
            "profile_completeness": evidence.get("profile_completeness"),
            "premium_account": evidence.get("premium_account", False),
            "profile_views": evidence.get("profile_views"),
            "industry": evidence.get("industry"),
            "location": evidence.get("location"),

            # Extraction details
            "sections_extracted": evidence.get("sections_extracted", []),
            "extraction_completeness": evidence.get("completeness_score", 0),
            "privacy_limitations": evidence.get("privacy_limitations", []),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            name = profile_data["basic_info"].get("name", "Unknown")
            title = profile_data["basic_info"].get("headline", "")
            success_message = f"Successfully extracted profile data for {name}"
            if title:
                success_message += f" ({title[:50]}...)" if len(title) > 50 else f" ({title})"
        else:
            success_message = f"Failed to extract LinkedIn profile: {claude_message}"

        # Get final screenshot
        final_screenshot = None
        if screenshots:
            final_screenshot = screenshots[-1].get("image_b64") if screenshots[-1] else None

        if not final_screenshot:
            final_screenshot = await self.capture_screenshot()

        return {
            "status": status,
            "message": success_message,
            "data": profile_data,
            "screenshot": final_screenshot,
            "timestamp": time.time(),
            "execution_details": {
                "screenshots_captured": len(screenshots),
                "claude_response": claude_message,
                "session_id": self.session_id
            }
        }


class LinkedInConnectionRequestAction(BaseAction):
    """Send personalized connection requests on LinkedIn."""

    # Action metadata
    name = "LinkedIn Connection Request"
    description = "Send personalized connection requests to LinkedIn profiles"
    category = "professional"
    tags = ["linkedin", "networking", "connections", "outreach"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 90
    estimated_duration_seconds = 30
    success_rate_threshold = 0.75

    # Parameter schema
    parameters = {
        "profile_url": {
            "type": "string",
            "required": True,
            "description": "LinkedIn profile URL to send connection request to"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "LinkedIn login credentials"
        },
        "message": {
            "type": "string",
            "required": False,
            "max_length": 300,
            "description": "Personalized connection message (optional, max 300 chars)"
        },
        "connection_reason": {
            "type": "string",
            "required": False,
            "description": "Reason for connection (colleague, classmate, friend, etc.)"
        }
    }

    async def execute(self, profile_url: str, credentials: dict[str, str],
                     message: str | None = None,
                     connection_reason: str = "other") -> dict[str, Any]:
        """
        Execute LinkedIn connection request sending.

        Args:
            profile_url: Target LinkedIn profile URL
            credentials: LinkedIn login credentials
            message: Optional personalized message
            connection_reason: Reason for connection

        Returns:
            Dict containing connection request results
        """
        if not self._is_valid_linkedin_url(profile_url):
            raise ActionValidationError(
                "Invalid LinkedIn profile URL provided",
                parameter="profile_url"
            )

        if message and len(message) > 300:
            raise ActionValidationError(
                "Connection message cannot exceed 300 characters",
                parameter="message"
            )

        logger.info("Starting LinkedIn connection request action",
                   url=profile_url,
                   has_message=bool(message),
                   reason=connection_reason,
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

            task_description = self._build_connection_task_description(
                profile_url, credentials, message, connection_reason
            )
            context = {
                "action": "linkedin_connection_request",
                "profile_url": profile_url,
                "message": message,
                "connection_reason": connection_reason,
                "platform": "linkedin.com"
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_connection_result(result, profile_url, message)

        except Exception as e:
            logger.error("LinkedIn connection request action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to send LinkedIn connection request: {str(e)}",
                error_code="LINKEDIN_CONNECTION_ERROR",
                details={
                    "profile_url": profile_url,
                    "message": message,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _is_valid_linkedin_url(self, url: str) -> bool:
        """Validate LinkedIn profile URL."""
        try:
            parsed = urlparse(url.lower())
            valid_domains = ["linkedin.com", "www.linkedin.com"]

            if parsed.netloc not in valid_domains:
                return False

            profile_patterns = ["/in/", "/pub/"]
            return any(pattern in parsed.path for pattern in profile_patterns)

        except Exception:
            return False

    def _build_connection_task_description(self, profile_url: str, credentials: dict[str, str],
                                         message: str | None, connection_reason: str) -> str:
        """Build task description for LinkedIn connection request."""

        task = f"""
Complete a LinkedIn connection request task:

1. NAVIGATE to LinkedIn.com
2. LOGIN with provided credentials:
   - Handle any security challenges appropriately
   - Navigate login process variations
3. NAVIGATE to the target profile: {profile_url}
4. WAIT for profile to load completely
5. LOCATE and CLICK the "Connect" button
6. HANDLE the connection request dialog:
   - {"ADD personalized message: '" + message + "'" if message else "Send without personalized message"}
   - Select appropriate connection reason if prompted
   - Review and confirm the request details
7. SEND the connection request
8. VERIFY the request was sent successfully
9. TAKE screenshots showing the process and confirmation

PROFILE URL: {profile_url}
{"PERSONALIZED MESSAGE: '" + message + "'" if message else "NO PERSONALIZED MESSAGE"}
CONNECTION REASON: {connection_reason}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

CONNECTION REQUEST REQUIREMENTS:
- Navigate to the exact profile URL
- Locate the correct "Connect" button (not "Follow" or "Message")
- Handle different profile layouts and connection button variations
- {"Include the provided personalized message exactly as written" if message else "Send connection request without additional message"}
- Select appropriate connection reason from LinkedIn's options
- Confirm the request before sending
- Verify successful sending with confirmation message

LINKEDIN INTERACTION PATTERNS:
- Use human-like timing and interaction patterns
- Handle LinkedIn's various UI states and A/B tests
- Manage rate limiting by LinkedIn appropriately
- Deal with premium vs. free account differences
- Handle already-connected profiles gracefully
- Manage pending request scenarios

SUCCESS CRITERIA:
- Successfully logged into LinkedIn
- Navigated to the target profile
- Found and clicked the connect button
- {"Added personalized message successfully" if message else "Proceeded without personalized message"}
- Connection request sent and confirmed
- Clear confirmation of successful sending

ERROR HANDLING:
- Handle already-connected profiles (note the existing connection)
- Deal with profiles that don't allow connection requests
- Manage LinkedIn's connection limits if reached
- Handle network issues and page load problems
- Report if the profile is not accessible or private
- Handle various LinkedIn error states appropriately

COMPLIANCE AND ETHICS:
- Respect LinkedIn's terms of service
- Follow professional networking etiquette
- Don't send spam or inappropriate requests
- Handle rejection or limits gracefully
- Maintain appropriate request frequency
"""

        return task.strip()

    async def _process_connection_result(self, agent_result: dict[str, Any],
                                       profile_url: str, message: str | None) -> dict[str, Any]:
        """Process Claude agent result for connection request."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "profile_url": profile_url,
            "personalized_message": message,
            "request_sent": evidence.get("request_sent", False),
            "target_profile": evidence.get("target_profile", {}),
            "connection_status": evidence.get("connection_status", "unknown"),
            "linkedin_response": evidence.get("linkedin_response", ""),
            "request_timestamp": time.time(),
            "final_url": agent_result.get("final_url", profile_url),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success" and result_data["request_sent"]:
            target_name = result_data["target_profile"].get("name", "LinkedIn member")
            success_message = f"Connection request sent to {target_name}"
            if message:
                success_message += " with personalized message"
        elif status == "success" and not result_data["request_sent"]:
            success_message = "Connection not sent - " + result_data["connection_status"]
        else:
            success_message = f"Failed to send connection request: {claude_message}"

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


class LinkedInJobSearchAction(BaseAction):
    """Search for jobs on LinkedIn and extract job posting details."""

    # Action metadata
    name = "LinkedIn Job Search"
    description = "Search for jobs on LinkedIn and extract detailed job posting information"
    category = "professional"
    tags = ["linkedin", "jobs", "search", "career", "employment"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 150  # Job searches can be lengthy
    estimated_duration_seconds = 90
    success_rate_threshold = 0.75

    # Parameter schema
    parameters = {
        "search_query": {
            "type": "string",
            "required": True,
            "min_length": 2,
            "max_length": 100,
            "description": "Job search query (title, keywords, company)"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "LinkedIn login credentials"
        },
        "location": {
            "type": "string",
            "required": False,
            "description": "Job location (city, state, country, or 'remote')"
        },
        "filters": {
            "type": "object",
            "required": False,
            "properties": {
                "date_posted": {"type": "string"},  # past-24h, past-week, past-month
                "experience_level": {"type": "string"},  # internship, entry, associate, mid, director
                "job_type": {"type": "string"},  # full-time, part-time, contract, temporary
                "remote": {"type": "boolean"},
                "salary_range": {"type": "string"}
            },
            "description": "Job search filters"
        },
        "max_results": {
            "type": "integer",
            "required": False,
            "min_value": 1,
            "max_value": 50,
            "description": "Maximum number of job results to extract (default 10)"
        },
        "extract_details": {
            "type": "boolean",
            "required": False,
            "description": "Extract detailed job posting information"
        }
    }

    async def execute(self, search_query: str, credentials: dict[str, str],
                     location: str | None = None, filters: dict | None = None,
                     max_results: int = 10, extract_details: bool = True) -> dict[str, Any]:
        """
        Execute LinkedIn job search and extraction.

        Args:
            search_query: Job search query
            credentials: LinkedIn credentials
            location: Job location
            filters: Search filters
            max_results: Maximum results to extract
            extract_details: Whether to extract detailed job info

        Returns:
            Dict containing job search results
        """
        if max_results > 50:
            raise ActionValidationError(
                "max_results cannot exceed 50",
                parameter="max_results"
            )

        logger.info("Starting LinkedIn job search action",
                   query=search_query,
                   location=location,
                   max_results=max_results,
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
            api_timeout=150000,
            block_ads=False
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_job_search_task_description(
                search_query, credentials, location, filters, max_results, extract_details
            )
            context = {
                "action": "linkedin_job_search",
                "search_query": search_query,
                "location": location,
                "filters": filters,
                "max_results": max_results,
                "extract_details": extract_details
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_job_search_result(result, search_query, location, max_results)

        except Exception as e:
            logger.error("LinkedIn job search action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to search LinkedIn jobs: {str(e)}",
                error_code="LINKEDIN_JOB_SEARCH_ERROR",
                details={
                    "search_query": search_query,
                    "location": location,
                    "filters": filters,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_job_search_task_description(self, search_query: str, credentials: dict[str, str],
                                         location: str | None, filters: dict | None,
                                         max_results: int, extract_details: bool) -> str:
        """Build task description for LinkedIn job search."""

        filter_text = ""
        if filters:
            filter_parts = []
            if filters.get("date_posted"):
                filter_parts.append(f"- Date Posted: {filters['date_posted']}")
            if filters.get("experience_level"):
                filter_parts.append(f"- Experience Level: {filters['experience_level']}")
            if filters.get("job_type"):
                filter_parts.append(f"- Job Type: {filters['job_type']}")
            if filters.get("remote"):
                filter_parts.append("- Remote: Yes")
            if filters.get("salary_range"):
                filter_parts.append(f"- Salary Range: {filters['salary_range']}")

            if filter_parts:
                filter_text = "APPLY SEARCH FILTERS:\n" + "\n".join(filter_parts) + "\n\n"

        task = f"""
Complete a LinkedIn job search and extraction task:

1. NAVIGATE to LinkedIn.com
2. LOGIN with provided credentials:
   - Handle security challenges appropriately
3. NAVIGATE to LinkedIn Jobs section (/jobs/)
4. PERFORM JOB SEARCH:
   - Search Query: "{search_query}"
   {"- Location: " + location if location else "- Location: Any"}

{filter_text}5. EXTRACT job information from search results (up to {max_results} jobs):

BASIC JOB INFO (always extract):
- Job title
- Company name
- Location
- Job posting date
- Job URL/ID
- Quick job description/summary

{"DETAILED JOB INFO (if extract_details=True):" if extract_details else ""}
{"""- Full job description
- Required qualifications/skills
- Preferred qualifications
- Salary range (if available)
- Benefits information
- Company information
- Seniority level
- Employment type (full-time, contract, etc.)
- Industry
- Job function
- Number of applicants (if visible)""" if extract_details else ""}

6. NAVIGATE through search results:
   - Handle pagination if needed for max_results
   - {"Click into individual job postings for detailed information" if extract_details else "Extract information from search results page"}
   - Respect LinkedIn's loading and interaction patterns
7. TAKE screenshots of search results and job details
8. COMPILE all extracted job data into structured format

SEARCH PARAMETERS:
- Query: "{search_query}"
{"- Location: " + location if location else ""}
- Max Results: {max_results}
- Extract Details: {extract_details}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

JOB EXTRACTION REQUIREMENTS:
- Extract accurate and complete job information
- Handle LinkedIn's dynamic content loading
- Preserve formatting in job descriptions
- Note any missing information clearly
- Extract dates in consistent format
- Handle premium vs. free account limitations
- Respect LinkedIn's rate limiting

LINKEDIN JOB SEARCH NAVIGATION:
- Use LinkedIn's native job search functionality
- Handle search result variations and layouts
- Manage job posting page structures
- Deal with "Easy Apply" vs external application processes
- Handle sponsored vs. organic job listings
- Navigate LinkedIn's job recommendation features

SUCCESS CRITERIA:
- Successfully logged into LinkedIn
- Performed job search with specified parameters
- {"Applied all requested filters correctly" if filters else ""}
- Extracted information from up to {max_results} relevant jobs
- {"Collected detailed job posting information" if extract_details else "Collected basic job information"}
- Data is complete and well-structured
- Clear screenshots document the search process

ERROR HANDLING:
- Handle no search results gracefully
- Deal with login and access issues
- Manage LinkedIn's anti-scraping measures
- Handle job postings that are removed or private
- Report any search limitations encountered
- Adapt to LinkedIn UI changes and variations

PERFORMANCE OPTIMIZATION:
- Batch similar operations when possible
- Minimize unnecessary page loads and clicks
- Handle large result sets efficiently
- Optimize scrolling and pagination
- Balance speed with thoroughness
"""

        return task.strip()

    async def _process_job_search_result(self, agent_result: dict[str, Any],
                                       search_query: str, location: str | None,
                                       max_results: int) -> dict[str, Any]:
        """Process Claude agent result for job search."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Extract job listings from evidence
        job_listings = evidence.get("job_listings", [])
        search_metadata = evidence.get("search_metadata", {})

        result_data = {
            "search_query": search_query,
            "location": location,
            "max_results_requested": max_results,
            "jobs_found": len(job_listings),
            "search_timestamp": time.time(),

            # Job listings
            "job_listings": job_listings,

            # Search metadata
            "search_metadata": {
                "total_results": search_metadata.get("total_results", 0),
                "pages_searched": search_metadata.get("pages_searched", 1),
                "filters_applied": search_metadata.get("filters_applied", []),
                "search_location": search_metadata.get("search_location", location),
                "result_types": search_metadata.get("result_types", [])
            },

            # Extraction details
            "extraction_completeness": evidence.get("completeness_score", 0),
            "failed_extractions": evidence.get("failed_extractions", []),
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            jobs_count = result_data["jobs_found"]
            total_results = result_data["search_metadata"]["total_results"]
            success_message = f"Found {jobs_count} job{'s' if jobs_count != 1 else ''} for '{search_query}'"
            if location:
                success_message += f" in {location}"
            if total_results > jobs_count:
                success_message += f" (showing {jobs_count} of {total_results} total)"
        else:
            success_message = f"Failed to search LinkedIn jobs: {claude_message}"

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


class LinkedInPostAction(BaseAction):
    """Create and publish posts on LinkedIn."""

    # Action metadata
    name = "LinkedIn Post"
    description = "Create and publish posts on your LinkedIn feed"
    category = "professional"
    tags = ["linkedin", "posting", "content", "social", "professional"]

    # Authentication required
    requires_auth = True

    # Performance settings
    timeout_seconds = 90
    estimated_duration_seconds = 30
    success_rate_threshold = 0.80

    # Parameter schema
    parameters = {
        "content": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 3000,
            "description": "Post content text (max 3000 characters)"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "LinkedIn login credentials"
        },
        "post_options": {
            "type": "object",
            "required": False,
            "properties": {
                "add_hashtags": {"type": "boolean", "default": False},
                "tag_people": {"type": "array", "items": {"type": "string"}},
                "share_to_groups": {"type": "boolean", "default": False}
            },
            "description": "Additional posting options"
        },
        "visibility": {
            "type": "string",
            "required": False,
            "description": "Post visibility: public, connections, or custom"
        }
    }

    async def execute(self, content: str, credentials: dict[str, str],
                     post_options: dict | None = None,
                     visibility: str = "public") -> dict[str, Any]:
        """
        Execute LinkedIn post creation and publishing.

        Args:
            content: Post content text
            credentials: LinkedIn credentials
            post_options: Additional posting options
            visibility: Post visibility setting

        Returns:
            Dict containing post creation results
        """
        if len(content) > 3000:
            raise ActionValidationError(
                "Post content cannot exceed 3000 characters",
                parameter="content"
            )

        if post_options is None:
            post_options = {}

        valid_visibility = ["public", "connections", "custom"]
        if visibility not in valid_visibility:
            raise ActionValidationError(
                f"Invalid visibility. Must be one of: {', '.join(valid_visibility)}",
                parameter="visibility"
            )

        logger.info("Starting LinkedIn post action",
                   content_length=len(content),
                   visibility=visibility,
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

            task_description = self._build_post_task_description(
                content, credentials, post_options, visibility
            )
            context = {
                "action": "linkedin_post",
                "content": content,
                "post_options": post_options,
                "visibility": visibility,
                "platform": "linkedin.com"
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_post_result(result, content, visibility)

        except Exception as e:
            logger.error("LinkedIn post action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to create LinkedIn post: {str(e)}",
                error_code="LINKEDIN_POST_ERROR",
                details={
                    "content": content[:100] + "..." if len(content) > 100 else content,
                    "visibility": visibility,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _build_post_task_description(self, content: str, credentials: dict[str, str],
                                   post_options: dict, visibility: str) -> str:
        """Build task description for LinkedIn post creation."""

        options_text = ""
        if post_options.get("add_hashtags"):
            options_text += "- Suggest and add relevant hashtags\n"
        if post_options.get("tag_people"):
            people = post_options["tag_people"]
            options_text += f"- Tag these people: {', '.join(people)}\n"
        if post_options.get("share_to_groups"):
            options_text += "- Consider sharing to relevant LinkedIn groups\n"

        task = f"""
Complete a LinkedIn post creation and publishing task:

1. NAVIGATE to LinkedIn.com
2. LOGIN with provided credentials:
   - Handle any security challenges appropriately
3. NAVIGATE to the LinkedIn feed/home page
4. LOCATE and CLICK the "Start a post" button or text area
5. CREATE the post with provided content:

POST CONTENT:
"{content}"

6. CONFIGURE post settings:
   - Set visibility to: {visibility.upper()}
   - {options_text if options_text else "Use default post settings"}

7. REVIEW the post preview carefully
8. PUBLISH the post by clicking "Post" button
9. VERIFY the post was published successfully
10. TAKE screenshots showing the posting process and final result

POST SETTINGS:
- Content: {len(content)} characters
- Visibility: {visibility.upper()}
- Additional Options: {bool(post_options)}

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

LINKEDIN POSTING REQUIREMENTS:
- Navigate to LinkedIn feed/home page
- Use the main post creation interface (not messaging or other areas)
- Include the exact content provided: "{content}"
- Set appropriate visibility settings
- Handle LinkedIn's post composer interface variations
- Verify post preview before publishing
- Confirm successful posting with visual confirmation

POST COMPOSITION BEST PRACTICES:
- Preserve line breaks and formatting in the content
- Handle hashtags and mentions appropriately
- Ensure proper spacing and readability
- Check character count and limits
- Handle emoji and special characters correctly
- Respect LinkedIn's professional content guidelines

SUCCESS CRITERIA:
- Successfully logged into LinkedIn
- Accessed the post creation interface
- Composed post with exact provided content
- Set visibility to {visibility}
- {"Applied additional posting options" if post_options else ""}
- Published post successfully
- Confirmed post appears in feed
- Clear screenshots document the process

ERROR HANDLING:
- Handle LinkedIn composer interface changes
- Deal with post publishing errors or limits
- Manage content that may trigger LinkedIn filters
- Handle network issues during publishing
- Report any post creation limitations
- Adapt to LinkedIn's various UI states

COMPLIANCE:
- Follow LinkedIn's community guidelines
- Respect professional networking standards
- Handle content moderation appropriately
- Ensure post meets LinkedIn's quality standards
- Maintain appropriate posting frequency
"""

        return task.strip()

    async def _process_post_result(self, agent_result: dict[str, Any],
                                 content: str, visibility: str) -> dict[str, Any]:
        """Process Claude agent result for LinkedIn post creation."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "post_content": content,
            "content_length": len(content),
            "visibility": visibility,
            "post_published": evidence.get("post_published", False),
            "post_url": evidence.get("post_url"),
            "post_id": evidence.get("post_id"),
            "publish_timestamp": time.time(),
            "linkedin_response": evidence.get("linkedin_response", ""),
            "final_url": agent_result.get("final_url"),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success" and result_data["post_published"]:
            success_message = f"Successfully published LinkedIn post ({len(content)} characters, {visibility} visibility)"
        elif status == "success" and not result_data["post_published"]:
            success_message = "Post created but not published - " + result_data["linkedin_response"]
        else:
            success_message = f"Failed to create LinkedIn post: {claude_message}"

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
