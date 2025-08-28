"""Bulk operations API endpoints."""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.stored_action import (
    StoredActionCreate,
    StoredActionUpdate,
)
from ...services.stored_actions import StoredActionService
from ..dependencies import get_current_user

router = APIRouter()
logger = structlog.get_logger(__name__)

stored_action_service = StoredActionService()


class BulkCreateRequest(BaseModel):
    """Request schema for bulk action creation."""
    actions: list[StoredActionCreate]


class BulkUpdateRequest(BaseModel):
    """Request schema for bulk action updates."""
    updates: list[dict[str, Any]]  # List of {id: str, data: StoredActionUpdate}


class BulkDeleteRequest(BaseModel):
    """Request schema for bulk action deletion."""
    action_ids: list[str]


class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations."""
    success: bool
    message: str
    processed_count: int
    failed_count: int
    results: list[dict[str, Any]]
    errors: list[dict[str, Any]]


@router.post("/create", response_model=BulkOperationResponse)
async def bulk_create_actions(
    request: BulkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple stored actions in bulk."""
    results = []
    errors = []
    processed_count = 0

    for i, action_data in enumerate(request.actions):
        try:
            action = await stored_action_service.create_stored_action(
                db=db,
                user_id=current_user.id,
                action_data=action_data,
            )
            results.append({
                "index": i,
                "id": action.id,
                "name": action.name,
                "status": "created"
            })
            processed_count += 1

        except Exception as e:
            logger.error("Failed to create action in bulk", index=i, error=str(e))
            errors.append({
                "index": i,
                "error": str(e),
                "action_name": action_data.name,
            })

    failed_count = len(errors)
    success = failed_count == 0

    return BulkOperationResponse(
        success=success,
        message=f"Processed {processed_count} actions, {failed_count} failed",
        processed_count=processed_count,
        failed_count=failed_count,
        results=results,
        errors=errors,
    )


@router.put("/update", response_model=BulkOperationResponse)
async def bulk_update_actions(
    request: BulkUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple stored actions in bulk."""
    results = []
    errors = []
    processed_count = 0

    for i, update_item in enumerate(request.updates):
        try:
            action_id = update_item.get("id")
            update_data = update_item.get("data")

            if not action_id or not update_data:
                raise ValueError("Both 'id' and 'data' are required")

            # Convert dict to Pydantic model
            action_update = StoredActionUpdate(**update_data)

            action = await stored_action_service.update_stored_action(
                db=db,
                action_id=action_id,
                user_id=current_user.id,
                action_data=action_update,
            )

            if action:
                results.append({
                    "index": i,
                    "id": action.id,
                    "name": action.name,
                    "status": "updated"
                })
                processed_count += 1
            else:
                errors.append({
                    "index": i,
                    "error": "Action not found",
                    "action_id": action_id,
                })

        except Exception as e:
            logger.error("Failed to update action in bulk", index=i, error=str(e))
            errors.append({
                "index": i,
                "error": str(e),
                "action_id": update_item.get("id"),
            })

    failed_count = len(errors)
    success = failed_count == 0

    return BulkOperationResponse(
        success=success,
        message=f"Processed {processed_count} actions, {failed_count} failed",
        processed_count=processed_count,
        failed_count=failed_count,
        results=results,
        errors=errors,
    )


@router.delete("/delete", response_model=BulkOperationResponse)
async def bulk_delete_actions(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple stored actions in bulk."""
    results = []
    errors = []
    processed_count = 0

    for i, action_id in enumerate(request.action_ids):
        try:
            success = await stored_action_service.delete_stored_action(
                db=db,
                action_id=action_id,
                user_id=current_user.id,
            )

            if success:
                results.append({
                    "index": i,
                    "id": action_id,
                    "status": "deleted"
                })
                processed_count += 1
            else:
                errors.append({
                    "index": i,
                    "error": "Action not found or access denied",
                    "action_id": action_id,
                })

        except Exception as e:
            logger.error("Failed to delete action in bulk", index=i, action_id=action_id, error=str(e))
            errors.append({
                "index": i,
                "error": str(e),
                "action_id": action_id,
            })

    failed_count = len(errors)
    success = failed_count == 0

    return BulkOperationResponse(
        success=success,
        message=f"Processed {processed_count} actions, {failed_count} failed",
        processed_count=processed_count,
        failed_count=failed_count,
        results=results,
        errors=errors,
    )


@router.post("/duplicate", response_model=BulkOperationResponse)
async def bulk_duplicate_actions(
    action_ids: list[str],
    name_suffix: str = " (Copy)",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate multiple stored actions in bulk."""
    results = []
    errors = []
    processed_count = 0

    for i, action_id in enumerate(action_ids):
        try:
            # Get the original action
            original_action = await stored_action_service.get_stored_action(
                db=db,
                action_id=action_id,
                user_id=current_user.id,
            )

            if not original_action:
                errors.append({
                    "index": i,
                    "error": "Original action not found",
                    "action_id": action_id,
                })
                continue

            # Create duplicate data
            duplicate_data = StoredActionCreate(
                name=original_action.name + name_suffix,
                description=original_action.description,
                action_type=original_action.action_type,
                configuration=original_action.configuration,
                tags=original_action.tags_list,
                is_public=original_action.is_public,
                webhook_url=None,  # Don't copy webhook URL
            )

            # Create the duplicate
            duplicate_action = await stored_action_service.create_stored_action(
                db=db,
                user_id=current_user.id,
                action_data=duplicate_data,
            )

            results.append({
                "index": i,
                "original_id": action_id,
                "duplicate_id": duplicate_action.id,
                "name": duplicate_action.name,
                "status": "duplicated"
            })
            processed_count += 1

        except Exception as e:
            logger.error("Failed to duplicate action in bulk", index=i, action_id=action_id, error=str(e))
            errors.append({
                "index": i,
                "error": str(e),
                "action_id": action_id,
            })

    failed_count = len(errors)
    success = failed_count == 0

    return BulkOperationResponse(
        success=success,
        message=f"Processed {processed_count} actions, {failed_count} failed",
        processed_count=processed_count,
        failed_count=failed_count,
        results=results,
        errors=errors,
    )


@router.post("/export", response_model=dict[str, Any])
async def bulk_export_actions(
    action_ids: list[str] | None = None,
    include_private: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export multiple stored actions in bulk."""
    try:
        if action_ids:
            # Export specific actions
            actions = []
            for action_id in action_ids:
                action = await stored_action_service.get_stored_action(
                    db=db,
                    action_id=action_id,
                    user_id=current_user.id,
                )
                if action:
                    actions.append(action)
        else:
            # Export all user's actions
            actions = await stored_action_service.list_stored_actions(
                db=db,
                user_id=current_user.id,
                skip=0,
                limit=1000,  # Export up to 1000 actions
            )

        # Format for export
        export_data = {
            "version": "1.0",
            "export_timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
            "actions": []
        }

        for action in actions:
            # Skip private actions if not requested
            if not include_private and not action.is_public:
                continue

            action_data = {
                "id": action.id,
                "name": action.name,
                "description": action.description,
                "action_type": action.action_type,
                "configuration": action.configuration,
                "tags": action.tags_list,
                "is_public": action.is_public,
                "created_at": action.created_at.isoformat(),
                "updated_at": action.updated_at.isoformat(),
            }

            # Don't include sensitive data
            if "webhook_url" in action_data["configuration"]:
                action_data["configuration"] = dict(action_data["configuration"])
                del action_data["configuration"]["webhook_url"]

            export_data["actions"].append(action_data)

        return {
            "success": True,
            "export_data": export_data,
            "exported_count": len(export_data["actions"]),
        }

    except Exception as e:
        logger.error("Failed to export actions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/import", response_model=BulkOperationResponse)
async def bulk_import_actions(
    import_data: dict[str, Any],
    skip_duplicates: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import multiple stored actions in bulk."""
    results = []
    errors = []
    processed_count = 0

    try:
        # Validate import data structure
        if "actions" not in import_data or not isinstance(import_data["actions"], list):
            raise ValueError("Invalid import data format")

        actions_data = import_data["actions"]

        for i, action_data in enumerate(actions_data):
            try:
                # Check for duplicate names if requested
                if skip_duplicates:
                    existing_actions = await stored_action_service.list_stored_actions(
                        db=db,
                        user_id=current_user.id,
                        skip=0,
                        limit=1000,
                    )

                    existing_names = {action.name for action in existing_actions}
                    if action_data.get("name") in existing_names:
                        action_data["name"] += f" (Imported {datetime.utcnow().strftime('%Y%m%d_%H%M%S')})"

                # Create action from import data
                create_data = StoredActionCreate(
                    name=action_data["name"],
                    description=action_data.get("description", ""),
                    action_type=action_data["action_type"],
                    configuration=action_data.get("configuration", {}),
                    tags=action_data.get("tags", []),
                    is_public=action_data.get("is_public", False),
                )

                action = await stored_action_service.create_stored_action(
                    db=db,
                    user_id=current_user.id,
                    action_data=create_data,
                )

                results.append({
                    "index": i,
                    "id": action.id,
                    "name": action.name,
                    "status": "imported"
                })
                processed_count += 1

            except Exception as e:
                logger.error("Failed to import action", index=i, error=str(e))
                errors.append({
                    "index": i,
                    "error": str(e),
                    "action_name": action_data.get("name", "Unknown"),
                })

        failed_count = len(errors)
        success = failed_count == 0

        return BulkOperationResponse(
            success=success,
            message=f"Processed {processed_count} actions, {failed_count} failed",
            processed_count=processed_count,
            failed_count=failed_count,
            results=results,
            errors=errors,
        )

    except Exception as e:
        logger.error("Failed bulk import", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )
