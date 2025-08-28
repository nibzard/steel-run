"""Credential management API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.credential import CredentialType
from ...models.user import User
from ...schemas.credential import (
    BulkCredentialResponse,
    CredentialCreate,
    CredentialResponse,
    CredentialUpdate,
    CredentialUsageStats,
    CredentialValidationRequest,
    CredentialValidationResponse,
)
from ...services.credential_service import CredentialService
from ..dependencies import get_current_user

router = APIRouter()
credential_service = CredentialService()


@router.post("/", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    credential_data: CredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new encrypted credential."""
    try:
        credential = await credential_service.create_credential(
            db=db,
            user_id=current_user.id,
            credential_data=credential_data,
        )
        return credential
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create credential",
        )


@router.get("/", response_model=list[CredentialResponse])
async def list_credentials(
    domain: str | None = Query(None, description="Filter by domain"),
    credential_type: CredentialType | None = Query(None, description="Filter by credential type"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    skip: int = Query(0, ge=0, description="Number of credentials to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of credentials to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's credentials with optional filtering."""
    credentials = await credential_service.list_credentials(
        db=db,
        user_id=current_user.id,
        domain=domain,
        credential_type=credential_type,
        tags=tags,
        skip=skip,
        limit=limit,
    )
    return credentials


@router.get("/domain/{domain}", response_model=list[CredentialResponse])
async def list_credentials_for_domain(
    domain: str,
    action_id: str | None = Query(None, description="Filter by action access"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List valid credentials for a specific domain."""
    credentials = await credential_service.list_credentials_for_domain(
        db=db,
        user_id=current_user.id,
        domain=domain,
        action_id=action_id,
    )
    return credentials


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific credential by ID."""
    credential = await credential_service.get_credential(
        db=db,
        credential_id=credential_id,
        user_id=current_user.id,
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    return credential


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    credential_data: CredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a credential."""
    try:
        credential = await credential_service.update_credential(
            db=db,
            credential_id=credential_id,
            user_id=current_user.id,
            credential_data=credential_data,
        )

        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found",
            )

        return credential
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credential",
        )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a credential."""
    success = await credential_service.delete_credential(
        db=db,
        credential_id=credential_id,
        user_id=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )


@router.post("/{credential_id}/validate", response_model=CredentialValidationResponse)
async def validate_credential(
    credential_id: str,
    validation_request: CredentialValidationRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a credential by testing its structure and optionally against a URL."""
    validation_url = validation_request.validation_url if validation_request else None

    result = await credential_service.validate_credential(
        db=db,
        credential_id=credential_id,
        user_id=current_user.id,
        validation_url=validation_url,
    )

    return result


@router.get("/{credential_id}/usage", response_model=list[CredentialUsageStats])
async def get_credential_usage_stats(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics for a specific credential."""
    # First check if credential exists and belongs to user
    credential = await credential_service.get_credential(
        db=db,
        credential_id=credential_id,
        user_id=current_user.id,
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    stats = await credential_service.get_credential_usage_stats(
        db=db,
        user_id=current_user.id,
        credential_id=credential_id,
    )

    return stats


@router.get("/stats/usage", response_model=list[CredentialUsageStats])
async def get_all_credentials_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics for all user credentials."""
    stats = await credential_service.get_credential_usage_stats(
        db=db,
        user_id=current_user.id,
    )

    return stats


@router.post("/bulk/delete", response_model=BulkCredentialResponse)
async def bulk_delete_credentials(
    credential_ids: list[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple credentials in bulk."""
    processed_count = 0
    failed_count = 0
    remaining_credentials = []

    for credential_id in credential_ids:
        try:
            success = await credential_service.delete_credential(
                db=db,
                credential_id=credential_id,
                user_id=current_user.id,
            )
            if success:
                processed_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1

    # Get remaining credentials
    remaining_credentials = await credential_service.list_credentials(
        db=db,
        user_id=current_user.id,
        skip=0,
        limit=1000,
    )

    return BulkCredentialResponse(
        success=failed_count == 0,
        message=f"Processed {processed_count} credentials, {failed_count} failed",
        processed_count=processed_count,
        failed_count=failed_count,
        credentials=remaining_credentials,
    )


@router.post("/bulk/validate", response_model=list[CredentialValidationResponse])
async def bulk_validate_credentials(
    credential_ids: list[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate multiple credentials in bulk."""
    results = []

    for credential_id in credential_ids:
        try:
            result = await credential_service.validate_credential(
                db=db,
                credential_id=credential_id,
                user_id=current_user.id,
            )
            results.append(result)
        except Exception as e:
            results.append(
                CredentialValidationResponse(
                    credential_id=credential_id,
                    is_valid=False,
                    validation_message=f"Validation failed: {str(e)}",
                    validated_at=datetime.utcnow(),
                )
            )

    return results
