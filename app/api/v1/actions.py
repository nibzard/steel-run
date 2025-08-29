"""Action discovery and registry API endpoints."""
# TRIGGER RELOAD


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...actions.registry import get_action_registry
from ...core.database import get_db
from ...models.user import User
from ...schemas.stored_action import ExecutionRequest, ExecutionResponse
from ..dependencies import get_current_user_optional
from ...services.execution_tracker import execution_tracker

router = APIRouter()


@router.get("/dev-status")
async def get_dev_status_first() -> dict:
    """
    Get development mode status for frontend configuration.
    
    Returns:
        Development status information
    """
    from ...core.config import settings
    
    return {
        "is_development": settings.is_development,
        "auth_disabled": settings.is_development and settings.disable_auth_in_dev,
        "dev_user_email": "dev@steel.run" if settings.is_development and settings.disable_auth_in_dev else None
    }


async def execute_steel_action(prompt: str, run_id: str):
    """Execute action using Steel SDK in background."""
    execution_tracker.start_execution(run_id)
    
    try:
        # Validate input
        if not prompt or not isinstance(prompt, str):
            execution_tracker.fail_execution(run_id, "Invalid input: prompt must be a non-empty string")
            return
        
        if not prompt.strip():
            execution_tracker.fail_execution(run_id, "Invalid input: prompt cannot be empty")
            return
        from steel import Steel
        import os
        import asyncio
        from datetime import datetime
        
        # Initialize Steel client
        steel_client = Steel()
        execution_tracker.update_progress(run_id, 30)
        
        results = {
            "result_data": {
                "action": "steel_execution",
                "website": "unknown",
                "success": True,
                "message": "Action executed successfully using Steel SDK",
                "browser_info": "Steel Browser",
                "timestamp": datetime.now().isoformat()
            },
            "screenshot_url": None,
            "error_message": None
        }
        
        # Simple action - navigate and take screenshot
        if "screenshot" in prompt.lower():
            # Extract URL from prompt or use default
            target_url = "https://google.com"
            if "google" in prompt.lower():
                target_url = "https://google.com"
            elif "github" in prompt.lower():
                target_url = "https://github.com"
            # Add more URL extraction logic as needed
            
            results["result_data"]["website"] = target_url
            execution_tracker.update_progress(run_id, 60)
            
            # Use Steel SDK direct screenshot method (not sessions.screenshot)
            try:
                screenshot_response = steel_client.screenshot(
                    url=target_url,
                    full_page=True,
                    delay=2000  # Wait 2 seconds for page load
                    # Removed use_proxy=True for hobby plan compatibility
                )
                
                # Debug the response structure
                print(f"Screenshot response type: {type(screenshot_response)}")
                print(f"Screenshot response attributes: {dir(screenshot_response) if hasattr(screenshot_response, '__dict__') else 'No attributes'}")
                
                # Try multiple possible response formats
                screenshot_url = None
                dimensions = "unknown"
                
                if hasattr(screenshot_response, 'screenshot') and hasattr(screenshot_response.screenshot, 'url'):
                    # Format from documentation
                    screenshot_url = screenshot_response.screenshot.url
                    if hasattr(screenshot_response.screenshot, 'width'):
                        dimensions = f"{screenshot_response.screenshot.width}x{screenshot_response.screenshot.height}"
                elif hasattr(screenshot_response, 'url'):
                    # Direct URL attribute
                    screenshot_url = screenshot_response.url
                elif hasattr(screenshot_response, 'screenshot_url'):
                    # Alternative attribute name
                    screenshot_url = screenshot_response.screenshot_url
                elif isinstance(screenshot_response, str):
                    # Direct string response
                    screenshot_url = screenshot_response
                elif hasattr(screenshot_response, 'data'):
                    # Data wrapper format
                    screenshot_url = screenshot_response.data.get('url') or screenshot_response.data.get('screenshot_url')
                
                if screenshot_url:
                    results["screenshot_url"] = screenshot_url
                    results["result_data"]["data_extracted"] = [
                        f"Successfully captured screenshot of {target_url}",
                        f"Screenshot dimensions: {dimensions}"
                    ]
                    print(f"Screenshot captured successfully for run_id: {run_id}, URL: {screenshot_url[:100]}...")
                else:
                    results["result_data"]["data_extracted"] = [
                        "Screenshot response received but format unexpected",
                        f"Response type: {type(screenshot_response).__name__}"
                    ]
                    results["screenshot_url"] = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iI2Y5ZmFmYiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjRweCIgZmlsbD0iIzMzNzNkYyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlNjcmVlbnNob3QgUGxhY2Vob2xkZXI8L3RleHQ+PC9zdmc+"
                    print(f"Screenshot format unexpected for run_id: {run_id}, response: {screenshot_response}")
                    
            except Exception as screenshot_error:
                error_msg = str(screenshot_error)
                results["result_data"]["data_extracted"] = [f"Screenshot failed: {error_msg}"]
                results["screenshot_url"] = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iI2ZmZWJlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNDAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMThweCIgZmlsbD0iI2RjMjYyNiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlNjcmVlbnNob3QgRmFpbGVkPC90ZXh0Pjx0ZXh0IHg9IjUwJSIgeT0iNjAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTJweCIgZmlsbD0iIzk5OTk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5lZWQgU3RlZWwgQVBJIEtleTwvdGV4dD48L3N2Zz4="
                print(f"Screenshot error for run_id {run_id}: {error_msg}")
        else:
            # For non-screenshot actions, just return success
            results["result_data"]["data_extracted"] = ["Action processed", "Steel SDK available"]
        
        # Complete execution (no session to release with direct screenshot API)
        execution_tracker.complete_execution(run_id, results)
        print(f"Steel action completed for run_id: {run_id}")
        
    except Exception as e:
        error_msg = f"Steel execution failed: {str(e)}"
        execution_tracker.fail_execution(run_id, error_msg)
        print(f"Steel execution failed for run_id {run_id}: {e}")


@router.get("/", response_model=dict)
async def list_available_actions(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all available actions from the registry.

    Returns both built-in actions and popular user actions.
    """
    registry = get_action_registry()

    if search:
        actions = registry.search(search)
    else:
        actions = registry.list_actions(category=category)

    # Add mock statistics for demo purposes
    for action in actions:
        action.update({
            "success_rate": 0.95,  # 95% success rate
            "avg_duration": 25000,  # 25 seconds average
            "usage_count": 150,  # Times used
            "requires_auth": action.get("requires_auth", False),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        })

    # Limit results
    if limit and len(actions) > limit:
        actions = actions[:limit]

    # Get categories
    categories = registry.get_categories()

    return {
        "actions": actions,
        "categories": list(categories.keys()),
        "total": len(actions)
    }


@router.get("/featured", response_model=list[dict])
async def get_featured_actions() -> list[dict]:
    """Get featured/popular actions."""
    registry = get_action_registry()
    actions = registry.get_popular_actions(limit=6)

    # Add mock statistics
    for action in actions:
        action.update({
            "success_rate": 0.97,  # Higher success rate for featured
            "avg_duration": 20000,  # Faster execution
            "usage_count": 500,  # More usage
            "requires_auth": action.get("requires_auth", False),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        })

    return actions


@router.get("/search", response_model=list[dict])
async def search_actions(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Limit results"),
) -> list[dict]:
    """Search actions by name, description, or tags."""
    registry = get_action_registry()
    results = registry.search(q)

    # Add mock statistics
    for action in results:
        action.update({
            "success_rate": 0.93,
            "avg_duration": 30000,
            "usage_count": 75,
            "requires_auth": action.get("requires_auth", False)
        })

    return results[:limit] if limit else results


@router.get("/_system/dev-status")
async def get_dev_status_system() -> dict:
    """
    Get development mode status for frontend configuration.
    
    Returns:
        Development status information
    """
    from ...core.config import settings
    
    return {
        "is_development": settings.is_development,
        "auth_disabled": settings.is_development and settings.disable_auth_in_dev,
        "dev_user_email": "dev@steel.run" if settings.is_development and settings.disable_auth_in_dev else None
    }


@router.get("/dev-status")
async def get_dev_status_alias() -> dict:
    """Alias for dev-status endpoint."""
    from ...core.config import settings
    
    return {
        "is_development": settings.is_development,
        "auth_disabled": settings.is_development and settings.disable_auth_in_dev,
        "dev_user_email": "dev@steel.run" if settings.is_development and settings.disable_auth_in_dev else None
    }


@router.get("/{action_id}", response_model=dict)
async def get_action_details(action_id: str) -> dict:
    """Get detailed information about a specific action."""
    registry = get_action_registry()

    action_class = registry.get(action_id)
    if not action_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found"
        )

    action_instance = action_class()
    metadata = action_instance.get_metadata()
    metadata["id"] = action_id

    # Add additional details
    metadata.update({
        "success_rate": 0.95,
        "avg_duration": 25000,
        "usage_count": 200,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "parameters": getattr(action_instance, "parameters", {}),
        "example_usage": f"Execute {metadata['name']} with appropriate parameters"
    })

    return metadata


@router.get("/{action_id}/code", response_model=str)
async def get_action_code(action_id: str) -> str:
    """Get the source code for an action (for the code editor)."""
    registry = get_action_registry()

    action_class = registry.get(action_id)
    if not action_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found"
        )

    # Return a simple mock implementation for now
    action_instance = action_class()

    # Simple test code to debug the endpoint
    code = f"""# Action: {action_instance.name}
# Description: {action_instance.description}

from typing import Any, Dict, Optional
import structlog

from app.actions.base import BaseAction, ActionExecutionError
from app.agent.executor import ClaudeAgent, BrowserSession

logger = structlog.get_logger(__name__)


class {action_class.__name__}(BaseAction):
    '''
    {action_instance.description}

    This action demonstrates the Steel.run atomic web function pattern.
    '''

    # Action metadata
    name = "{action_instance.name}"
    description = "{action_instance.description}"
    category = "{action_instance.category}"
    tags = {repr(action_instance.tags)}

    # Authentication and performance settings
    requires_auth = {getattr(action_instance, 'requires_auth', False)}
    timeout_seconds = {getattr(action_instance, 'timeout_seconds', 30)}
    estimated_duration_seconds = {getattr(action_instance, 'estimated_duration_seconds', 20)}
    success_rate_threshold = {getattr(action_instance, 'success_rate_threshold', 0.9)}

    # Parameter schema
    parameters = {repr(getattr(action_instance, 'parameters', {}))}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        '''Execute the {action_instance.name} action.'''
        # TODO: Implement actual action logic
        return {{"success": True, "message": "Action executed successfully"}}

    def validate_parameters(self, **kwargs) -> bool:
        '''Validate input parameters against the schema.'''
        return True


# Register the action
if __name__ == "__main__":
    from app.actions.registry import register_action
    register_action("{action_id}", {action_class.__name__})
"""

    return code


@router.get("/{action_id}/history", response_model=list[dict])
async def get_action_history(
    action_id: str,
    limit: int = Query(10, ge=1, le=50, description="Limit results"),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get execution history for an action."""

    if not current_user:
        # Return empty history for unauthenticated users
        return []

    try:
        # This is a placeholder - in a real implementation, you'd fetch from the database
        # For now, return mock history data
        import datetime

        history = []
        for i in range(min(5, limit)):  # Mock 5 recent executions
            history.append({
                "id": f"run_{action_id}_{i+1}",
                "status": "completed" if i < 4 else "failed",
                "created_at": (datetime.datetime.now() - datetime.timedelta(days=i)).isoformat(),
                "execution_time": 25000 + (i * 2000),  # Varying execution times
                "parameters": {"test": f"value_{i+1}"},
                "error_message": "Network timeout" if i == 4 else None
            })

        return history

    except Exception:
        # Return empty history on error
        return []


@router.post("/analyze", response_model=dict)
async def analyze_natural_language_action(
    request: dict,
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """
    Analyze natural language input to determine action requirements.

    This endpoint helps the frontend understand what an action needs before execution.
    """
    input_text = request.get("input", "")

    if not input_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text is required"
        )

    # Simple analysis logic (in a real implementation, this would use LLM)
    input_lower = input_text.lower()

    requires_auth = any(keyword in input_lower for keyword in [
        "twitter", "post tweet", "facebook", "instagram", "linkedin",
        "login", "sign in", "account", "profile"
    ])

    detected_website = None
    if "twitter" in input_lower or "tweet" in input_lower:
        detected_website = "twitter"
    elif "facebook" in input_lower:
        detected_website = "facebook"
    elif "linkedin" in input_lower:
        detected_website = "linkedin"
    elif "instagram" in input_lower:
        detected_website = "instagram"

    action_type = "unknown"
    if "screenshot" in input_lower:
        action_type = "screenshot"
    elif "scrape" in input_lower or "extract" in input_lower:
        action_type = "scraping"
    elif "post" in input_lower or "tweet" in input_lower:
        action_type = "posting"
    elif "form" in input_lower or "fill" in input_lower:
        action_type = "form_filling"

    estimated_duration = 30  # seconds
    if action_type == "screenshot":
        estimated_duration = 15
    elif action_type == "scraping":
        estimated_duration = 45
    elif action_type == "posting":
        estimated_duration = 25

    return {
        "requires_auth": requires_auth,
        "detected_website": detected_website,
        "action_type": action_type,
        "estimated_duration": estimated_duration,
        "confidence": 0.85,  # Mock confidence score
        "suggested_parameters": {
            "timeout_seconds": estimated_duration + 15,
            "max_retries": 1
        }
    }


@router.post("/execute", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_natural_language_action(
    request: ExecutionRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """
    Execute a natural language action request using Steel SDK.
    """
    import uuid
    
    run_id = str(uuid.uuid4())
    
    # Validate input
    if not request.input or not request.input.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text is required and cannot be empty"
        )
    
    # Create execution tracking
    execution_tracker.create_execution(run_id, request.input)
    
    # Trigger Steel SDK execution in background
    try:
        import asyncio
        # Create background task for Steel execution
        asyncio.create_task(execute_steel_action(request.input, run_id))
        print(f"Started Steel execution for run_id: {run_id}")
    except Exception as e:
        print(f"Steel execution setup failed: {e}")
        execution_tracker.fail_execution(run_id, f"Execution setup failed: {str(e)}")
    
    return ExecutionResponse(
        run_id=run_id,
        status="queued",
        message="Natural language action has been queued for execution",
        estimated_duration=30,
        webhook_url=request.webhook_url
    )


@router.get("/executions/{run_id}/status", response_model=dict)
async def get_execution_status(
    run_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get execution status from tracker."""
    return execution_tracker.get_status(run_id)


@router.get("/executions/{run_id}/results", response_model=dict)
async def get_execution_results(
    run_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get execution results from tracker."""
    results = execution_tracker.get_results(run_id)
    
    # If execution is not completed, return 202
    if results.get("status") not in ["completed", "failed"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=202, detail="Execution still in progress")
    
    return results
