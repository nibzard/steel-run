"""Bootstrap and initialize actions for Steel.run."""

import structlog

from .amazon import (
    AmazonCartManagementAction,
    AmazonPriceCheckAction,
    AmazonProductDetailsAction,
)
from .gmail import (
    GmailReadEmailsAction,
    GmailSearchAction,
    GmailSendEmailAction,
    GmailUnreadCountAction,
)
from .linkedin import (
    LinkedInConnectionRequestAction,
    LinkedInJobSearchAction,
    LinkedInPostAction,
    LinkedInProfileExtractorAction,
)
from .registry import get_action_registry, register_action
from .twitter import TwitterPostAction, TwitterReplyAction
from .website import (
    WebsiteContentAction,
    WebsiteFormFillerAction,
    WebsiteScreenshotAction,
)

logger = structlog.get_logger(__name__)


def initialize_actions() -> None:
    """Initialize and register all built-in actions."""
    logger.info("Initializing Steel.run actions")

    # Website actions
    register_action("website-screenshot", WebsiteScreenshotAction)
    register_action("website-content", WebsiteContentAction)
    register_action("website-form-filler", WebsiteFormFillerAction)

    # Twitter/X.com actions
    register_action("twitter-post", TwitterPostAction)
    register_action("twitter-reply", TwitterReplyAction)

    # Amazon actions
    register_action("amazon-price-check", AmazonPriceCheckAction)
    register_action("amazon-product-details", AmazonProductDetailsAction)
    register_action("amazon-cart-management", AmazonCartManagementAction)

    # LinkedIn actions
    register_action("linkedin-profile-extractor", LinkedInProfileExtractorAction)
    register_action("linkedin-connection-request", LinkedInConnectionRequestAction)
    register_action("linkedin-job-search", LinkedInJobSearchAction)
    register_action("linkedin-post", LinkedInPostAction)

    # Gmail actions
    register_action("gmail-unread-count", GmailUnreadCountAction)
    register_action("gmail-read-emails", GmailReadEmailsAction)
    register_action("gmail-send-email", GmailSendEmailAction)
    register_action("gmail-search", GmailSearchAction)

    registry = get_action_registry()
    total_actions = registry.get_action_count()
    categories = registry.get_categories()

    logger.info(
        "Action initialization complete",
        total_actions=total_actions,
        categories=list(categories.keys()),
    )


def get_featured_actions() -> list:
    """Get a curated list of featured actions for the dashboard."""
    registry = get_action_registry()

    # Define featured action IDs in order of prominence
    featured_ids = [
        "website-screenshot",
        "website-content",
        "twitter-post",
        "amazon-price-check",
        "linkedin-profile-extractor",
        "gmail-unread-count",
        "website-form-filler",
        "linkedin-job-search",
        "gmail-send-email",
        "twitter-reply",
        "amazon-product-details",
        "linkedin-connection-request",
    ]

    featured_actions = []
    for action_id in featured_ids:
        if registry.validate_action_id(action_id):
            instance = registry.create_instance(action_id)
            if instance:
                metadata = instance.get_metadata()
                metadata["id"] = action_id
                featured_actions.append(metadata)

    return featured_actions


def get_action_examples() -> dict:
    """Get example natural language inputs for each action."""
    return {
        "website-screenshot": [
            "Take a screenshot of google.com",
            "Capture a full page screenshot of https://example.com",
            "Screenshot apple.com with 1920x1080 resolution",
        ],
        "website-content": [
            "Extract text content from https://news.ycombinator.com",
            "Get the content from wikipedia.org/wiki/Python in markdown format",
            "Scrape text from reddit.com/r/programming including links",
        ],
        "twitter-post": [
            "Post 'Hello World!' to Twitter",
            "Tweet about my latest project launch",
            "Share an update about Steel.run on X",
        ],
        "twitter-reply": [
            "Reply to a tweet with encouragement",
            "Respond to a Twitter thread with insights",
            "Reply to @username with thanks",
        ],
        "website-form-filler": [
            "Fill out contact form on example.com with my details",
            "Submit job application form with my information",
            "Fill registration form and submit it",
        ],
        "website-data-extractor": [
            "Extract product prices from shopping website",
            "Scrape job listings from careers page",
            "Get all article titles from news homepage",
        ],
        "amazon-price-check": [
            "Check Amazon price for iPhone 15",
            "Find the best deals on laptops under $1000",
            "Monitor MacBook Pro pricing on Amazon",
        ],
        "amazon-product-details": [
            "Get detailed product info for iPhone on Amazon",
            "Extract reviews and specs for laptop",
            "Analyze product features and ratings",
        ],
        "amazon-cart-management": [
            "Add iPhone to my Amazon cart",
            "View my current Amazon shopping cart",
            "Remove items from Amazon cart",
        ],
        "linkedin-profile-extractor": [
            "Extract profile data from LinkedIn user",
            "Get work experience from LinkedIn profile",
            "Analyze skills and connections from profile",
        ],
        "linkedin-connection-request": [
            "Send connection request on LinkedIn",
            "Connect with person on LinkedIn with message",
            "Send personalized LinkedIn connection",
        ],
        "linkedin-job-search": [
            "Search for software engineer jobs on LinkedIn",
            "Find remote Python developer positions",
            "Look for marketing jobs in San Francisco",
        ],
        "linkedin-post": [
            "Post update about my new project on LinkedIn",
            "Share professional achievement on LinkedIn",
            "Write LinkedIn post about industry trends",
        ],
        "gmail-unread-count": [
            "Check how many unread emails I have",
            "Get Gmail unread count by category",
            "Count unread emails in specific labels",
        ],
        "gmail-read-emails": [
            "Read my latest unread Gmail emails",
            "Find emails from specific sender",
            "Read emails with attachments from today",
        ],
        "gmail-send-email": [
            "Send email to team about meeting",
            "Compose and send follow-up email",
            "Email proposal to client with formatting",
        ],
        "gmail-search": [
            "Search Gmail for emails from last week",
            "Find emails with specific subject line",
            "Search for emails with attachments from sender",
        ],
    }


def get_actions_by_category() -> dict:
    """Get actions organized by category."""
    registry = get_action_registry()
    return registry.get_categories()


def get_action_performance_stats() -> dict:
    """Get performance statistics for all actions."""
    registry = get_action_registry()
    actions = {}

    for action_id in registry.get_all_action_ids():
        instance = registry.create_instance(action_id)
        if instance:
            metadata = instance.get_metadata()
            actions[action_id] = {
                "estimated_duration": metadata.get("estimated_duration_seconds", 30),
                "success_rate_threshold": metadata.get("success_rate_threshold", 0.8),
                "timeout_seconds": metadata.get("timeout_seconds", 60),
                "category": metadata.get("category", "general"),
                "requires_auth": metadata.get("requires_auth", False)
            }

    return actions
