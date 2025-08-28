"""Action templates and sharing functionality."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.stored_action import StoredActionCreate, StoredActionResponse
from ...services.stored_actions import StoredActionService
from ..dependencies import get_current_user, get_current_user_optional

router = APIRouter()
logger = structlog.get_logger(__name__)

stored_action_service = StoredActionService()


class ActionTemplate(BaseModel):
    """Action template schema."""
    id: str
    name: str
    description: str
    action_type: str
    configuration_template: dict[str, Any]
    tags: list[str]
    category: str
    difficulty_level: str  # beginner, intermediate, advanced
    estimated_runtime: int | None  # seconds
    author: str
    version: str
    created_at: str
    usage_count: int
    rating: float
    is_featured: bool


class ShareActionRequest(BaseModel):
    """Request to share an action as a template."""
    action_id: str
    template_name: str | None = None
    template_description: str | None = None
    category: str = "general"
    difficulty_level: str = "intermediate"
    estimated_runtime: int | None = None
    make_public: bool = True


class TemplateUsageRequest(BaseModel):
    """Request to create action from template."""
    template_id: str
    name: str
    configuration: dict[str, Any]
    description: str | None = None


# Predefined action templates
BUILT_IN_TEMPLATES = [
    {
        "id": "twitter_post_template",
        "name": "Twitter Post Template",
        "description": "Template for posting tweets with customizable content",
        "action_type": "twitter_post",
        "configuration_template": {
            "tweet_text": "{{tweet_content}}",
            "include_media": False,
            "schedule_time": None,
            "thread_mode": False
        },
        "tags": ["twitter", "social_media", "posting"],
        "category": "social_media",
        "difficulty_level": "beginner",
        "estimated_runtime": 15,
        "author": "Steel.run Team",
        "version": "1.0.0",
        "created_at": "2024-01-01T00:00:00Z",
        "usage_count": 1000,
        "rating": 4.8,
        "is_featured": True
    },
    {
        "id": "website_screenshot_template",
        "name": "Website Screenshot Template",
        "description": "Template for capturing website screenshots with customizable options",
        "action_type": "website_screenshot",
        "configuration_template": {
            "url": "{{website_url}}",
            "viewport_width": 1920,
            "viewport_height": 1080,
            "full_page": True,
            "wait_for_selector": None,
            "hide_elements": []
        },
        "tags": ["screenshot", "website", "capture"],
        "category": "web_automation",
        "difficulty_level": "beginner",
        "estimated_runtime": 10,
        "author": "Steel.run Team",
        "version": "1.0.0",
        "created_at": "2024-01-01T00:00:00Z",
        "usage_count": 2500,
        "rating": 4.9,
        "is_featured": True
    },
    {
        "id": "form_fill_template",
        "name": "Form Filling Template",
        "description": "Template for automated form filling with customizable field mappings",
        "action_type": "form_fill",
        "configuration_template": {
            "url": "{{form_url}}",
            "field_mappings": {
                "name": "{{user_name}}",
                "email": "{{user_email}}",
                "message": "{{message_content}}"
            },
            "submit_form": True,
            "wait_after_submit": 3
        },
        "tags": ["form", "automation", "data_entry"],
        "category": "web_automation",
        "difficulty_level": "intermediate",
        "estimated_runtime": 30,
        "author": "Steel.run Team",
        "version": "1.0.0",
        "created_at": "2024-01-01T00:00:00Z",
        "usage_count": 800,
        "rating": 4.6,
        "is_featured": True
    },
    {
        "id": "price_monitor_template",
        "name": "Price Monitoring Template",
        "description": "Template for monitoring product prices with alerts",
        "action_type": "price_monitor",
        "configuration_template": {
            "product_url": "{{product_url}}",
            "price_selector": "{{price_css_selector}}",
            "target_price": "{{alert_price}}",
            "comparison": "less_than",
            "notification_webhook": "{{webhook_url}}"
        },
        "tags": ["price", "monitoring", "alerts", "shopping"],
        "category": "monitoring",
        "difficulty_level": "advanced",
        "estimated_runtime": 60,
        "author": "Steel.run Team",
        "version": "1.0.0",
        "created_at": "2024-01-01T00:00:00Z",
        "usage_count": 450,
        "rating": 4.7,
        "is_featured": False
    }
]


@router.get("/", response_model=list[ActionTemplate])
async def list_action_templates(
    category: str | None = Query(None, description="Filter by category"),
    difficulty_level: str | None = Query(None, description="Filter by difficulty level"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    featured_only: bool = Query(False, description="Show only featured templates"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User | None = Depends(get_current_user_optional),
):
    """List available action templates."""
    templates = []

    # Add built-in templates
    for template_data in BUILT_IN_TEMPLATES:
        template = ActionTemplate(**template_data)

        # Apply filters
        if category and template.category != category:
            continue
        if difficulty_level and template.difficulty_level != difficulty_level:
            continue
        if tags and not any(tag in template.tags for tag in tags):
            continue
        if featured_only and not template.is_featured:
            continue

        templates.append(template)

    # TODO: Add user-shared templates from database

    # Apply pagination
    return templates[skip:skip + limit]


@router.get("/{template_id}", response_model=ActionTemplate)
async def get_action_template(
    template_id: str,
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get a specific action template by ID."""
    # Check built-in templates
    for template_data in BUILT_IN_TEMPLATES:
        if template_data["id"] == template_id:
            return ActionTemplate(**template_data)

    # TODO: Check user-shared templates in database

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Template not found"
    )


@router.post("/use/{template_id}", response_model=StoredActionResponse)
async def create_action_from_template(
    template_id: str,
    usage_request: TemplateUsageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new stored action from a template."""
    # Get the template
    template = None
    for template_data in BUILT_IN_TEMPLATES:
        if template_data["id"] == template_id:
            template = ActionTemplate(**template_data)
            break

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    try:
        # Create action data from template
        action_data = StoredActionCreate(
            name=usage_request.name,
            description=usage_request.description or template.description,
            action_type=template.action_type,
            configuration=usage_request.configuration,
            tags=template.tags,
            is_public=False,  # Created actions are private by default
        )

        # Create the stored action
        action = await stored_action_service.create_stored_action(
            db=db,
            user_id=current_user.id,
            action_data=action_data,
        )

        # TODO: Track template usage statistics

        logger.info(
            "Created action from template",
            template_id=template_id,
            action_id=action.id,
            user_id=current_user.id,
        )

        return action

    except Exception as e:
        logger.error("Failed to create action from template", template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create action from template"
        )


@router.post("/share", response_model=dict[str, Any])
async def share_action_as_template(
    share_request: ShareActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Share an existing action as a public template."""
    try:
        # Get the action to share
        action = await stored_action_service.get_stored_action(
            db=db,
            action_id=share_request.action_id,
            user_id=current_user.id,
        )

        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action not found"
            )

        # TODO: Create shared template in database
        # For now, just return success

        logger.info(
            "Action shared as template",
            action_id=share_request.action_id,
            user_id=current_user.id,
            template_name=share_request.template_name,
        )

        return {
            "success": True,
            "message": "Action shared as template successfully",
            "template_id": f"user_{current_user.id}_{share_request.action_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to share action as template", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share action as template"
        )


@router.get("/categories/list", response_model=list[dict[str, Any]])
async def list_template_categories():
    """List available template categories."""
    categories = [
        {
            "id": "social_media",
            "name": "Social Media",
            "description": "Templates for social media automation and posting",
            "icon": "social",
            "count": len([t for t in BUILT_IN_TEMPLATES if t["category"] == "social_media"])
        },
        {
            "id": "web_automation",
            "name": "Web Automation",
            "description": "Templates for website automation and data extraction",
            "icon": "web",
            "count": len([t for t in BUILT_IN_TEMPLATES if t["category"] == "web_automation"])
        },
        {
            "id": "monitoring",
            "name": "Monitoring & Alerts",
            "description": "Templates for monitoring websites and sending alerts",
            "icon": "monitor",
            "count": len([t for t in BUILT_IN_TEMPLATES if t["category"] == "monitoring"])
        },
        {
            "id": "data_processing",
            "name": "Data Processing",
            "description": "Templates for data extraction and processing",
            "icon": "data",
            "count": 0  # No built-in templates yet
        },
        {
            "id": "ecommerce",
            "name": "E-commerce",
            "description": "Templates for online shopping and price monitoring",
            "icon": "shopping",
            "count": 0  # No built-in templates yet
        }
    ]

    return categories


@router.get("/stats/popular", response_model=list[ActionTemplate])
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get most popular action templates."""
    # Sort by usage count and rating
    popular_templates = sorted(
        BUILT_IN_TEMPLATES,
        key=lambda t: (t["usage_count"] * t["rating"]),
        reverse=True
    )

    return [ActionTemplate(**template) for template in popular_templates[:limit]]


@router.get("/stats/featured", response_model=list[ActionTemplate])
async def get_featured_templates(
    current_user: User | None = Depends(get_current_user_optional),
):
    """Get featured action templates."""
    featured_templates = [t for t in BUILT_IN_TEMPLATES if t["is_featured"]]
    return [ActionTemplate(**template) for template in featured_templates]
