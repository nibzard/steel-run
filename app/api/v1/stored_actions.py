"""Stored actions CRUD API endpoints."""


from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.stored_action import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionResult,
    ExecutionStatus,
    StoredActionCreate,
    StoredActionListResponse,
    StoredActionResponse,
    StoredActionUpdate,
)
from ...services.stored_actions import StoredActionService
from ..dependencies import get_current_user, get_current_user_or_api_key

router = APIRouter()


@router.post("/save", response_model=StoredActionResponse, status_code=status.HTTP_201_CREATED)
async def save_stored_action(
    action_data: StoredActionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoredActionResponse:
    """
    Save a new user action configuration.

    Args:
        action_data: Action creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created stored action
    """
    stored_action = await StoredActionService.create_stored_action(
        db, current_user.id, action_data
    )

    # Convert to response model with computed fields
    response_data = StoredActionResponse.from_orm(stored_action).dict()
    response_data["api_endpoint"] = f"/api/v1/stored-actions/{stored_action.id}/run"

    return StoredActionResponse(**response_data)


@router.get("/user", response_model=StoredActionListResponse)
async def list_user_actions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    active_only: bool = Query(True, description="Return only active actions"),
    action_type: str | None = Query(None, description="Filter by action type"),
    search: str | None = Query(None, description="Search in name and description"),
) -> StoredActionListResponse:
    """
    List user's saved actions with pagination and filtering.

    Args:
        current_user: Current authenticated user
        db: Database session
        page: Page number (1-based)
        size: Number of items per page
        active_only: Whether to return only active actions
        action_type: Filter by action type
        search: Search term for name and description

    Returns:
        Paginated list of stored actions
    """
    skip = (page - 1) * size

    actions, total = await StoredActionService.get_user_actions(
        db,
        current_user.id,
        skip=skip,
        limit=size,
        active_only=active_only,
        action_type=action_type,
        search=search,
    )

    # Convert to response models
    action_responses = []
    for action in actions:
        response_data = StoredActionResponse.from_orm(action).dict()
        response_data["api_endpoint"] = f"/api/actions/{action.id}/run"
        action_responses.append(StoredActionResponse(**response_data))

    return StoredActionListResponse(
        actions=action_responses,
        total=total,
        page=page,
        size=size,
        has_next=skip + size < total,
        has_previous=page > 1,
    )


@router.get("/{action_id}", response_model=StoredActionResponse)
async def get_stored_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoredActionResponse:
    """
    Get a specific stored action.

    Args:
        action_id: Action ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Stored action details

    Raises:
        HTTPException: If action not found
    """
    stored_action = await StoredActionService.get_stored_action(
        db, current_user.id, action_id
    )

    if not stored_action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored action not found"
        )

    response_data = StoredActionResponse.from_orm(stored_action).dict()
    response_data["api_endpoint"] = f"/api/v1/stored-actions/{stored_action.id}/run"

    return StoredActionResponse(**response_data)


@router.put("/{action_id}", response_model=StoredActionResponse)
async def update_stored_action(
    action_id: str,
    action_data: StoredActionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StoredActionResponse:
    """
    Update a saved action.

    Args:
        action_id: Action ID
        action_data: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated stored action

    Raises:
        HTTPException: If action not found
    """
    stored_action = await StoredActionService.update_stored_action(
        db, current_user.id, action_id, action_data
    )

    if not stored_action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored action not found"
        )

    response_data = StoredActionResponse.from_orm(stored_action).dict()
    response_data["api_endpoint"] = f"/api/v1/stored-actions/{stored_action.id}/run"

    return StoredActionResponse(**response_data)


@router.delete("/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stored_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a saved action.

    Args:
        action_id: Action ID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If action not found
    """
    success = await StoredActionService.delete_stored_action(
        db, current_user.id, action_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored action not found"
        )


@router.post("/{action_id}/run", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_stored_action(
    action_id: str,
    execution_request: ExecutionRequest | None = None,
    request: Request = None,
    current_user: User = Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """
    Execute a stored action (for Zapier/n8n integration).

    This endpoint can be called with either JWT authentication or API key.
    It creates an execution run and returns immediately while processing asynchronously.

    Args:
        action_id: Action ID to execute
        execution_request: Optional execution parameters
        request: HTTP request (for logging)
        current_user: Current authenticated user (via JWT or API key)
        db: Database session

    Returns:
        Execution response with run ID and status

    Raises:
        HTTPException: If action not found or not accessible
    """
    # Get stored action
    stored_action = await StoredActionService.get_stored_action_by_id(db, action_id)

    if not stored_action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored action not found"
        )

    # Check if user has access to this action
    if stored_action.user_id != current_user.id and not stored_action.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this action is forbidden"
        )

    # Check if action is active
    if not stored_action.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action is not active"
        )

    # Create execution run
    execution_data = execution_request or ExecutionRequest()

    execution_run = await StoredActionService.create_execution_run(
        db=db,
        stored_action=stored_action,
        user_id=current_user.id,
        input_parameters=execution_data.parameters,
        webhook_url=str(execution_data.webhook_url) if execution_data.webhook_url else None,
        timeout_seconds=execution_data.timeout_seconds or 30,
        max_retries=execution_data.max_retries or 0,
        external_request_id=execution_data.external_request_id,
        triggered_by="api",
    )

    # Queue execution for background processing
    from ...services.execution_service import queue_action_execution
    await queue_action_execution(execution_run.id)

    return ExecutionResponse(
        run_id=execution_run.id,
        status=execution_run.status,
        message=f"Execution queued for action '{stored_action.name}'",
        estimated_duration=stored_action.avg_execution_time or 30000,  # milliseconds
        webhook_url=execution_run.webhook_url,
    )


@router.get("/{action_id}/status/{run_id}", response_model=ExecutionStatus)
async def get_execution_status(
    action_id: str,
    run_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
) -> ExecutionStatus:
    """
    Check execution status.

    Args:
        action_id: Action ID
        run_id: Execution run ID
        request: HTTP request
        current_user: Current authenticated user (via JWT or API key)
        db: Database session

    Returns:
        Execution status information

    Raises:
        HTTPException: If execution run not found or not accessible
    """
    execution_run = await StoredActionService.get_execution_run(db, action_id, run_id)

    if not execution_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution run not found"
        )

    # Check if user has access to this execution
    if execution_run.user_id != current_user.id:
        # Check if user owns the action and it's public
        stored_action = await StoredActionService.get_stored_action_by_id(db, action_id)
        if not stored_action or (stored_action.user_id != current_user.id and not stored_action.is_public):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this execution is forbidden"
            )

    return ExecutionStatus.from_orm(execution_run)


@router.get("/{action_id}/results/{run_id}", response_model=ExecutionResult)
async def get_execution_results(
    action_id: str,
    run_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
) -> ExecutionResult:
    """
    Get execution results.

    Args:
        action_id: Action ID
        run_id: Execution run ID
        request: HTTP request
        current_user: Current authenticated user (via JWT or API key)
        db: Database session

    Returns:
        Execution results and output data

    Raises:
        HTTPException: If execution run not found or not accessible
    """
    execution_run = await StoredActionService.get_execution_run(db, action_id, run_id)

    if not execution_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution run not found"
        )

    # Check if user has access to this execution
    if execution_run.user_id != current_user.id:
        # Check if user owns the action and it's public
        stored_action = await StoredActionService.get_stored_action_by_id(db, action_id)
        if not stored_action or (stored_action.user_id != current_user.id and not stored_action.is_public):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this execution is forbidden"
            )

    return ExecutionResult.from_orm(execution_run)
