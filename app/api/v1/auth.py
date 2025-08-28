"""Authentication endpoints for user management and API keys."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_db
from ...models.user import User
from ...schemas.auth import (
    APIKeyCreate,
    APIKeyGenerated,
    APIKeyResponse,
    PasswordChange,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from ...services.auth_service import AuthService
from ...utils.auth import create_access_token
from ..dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user information

    Raises:
        HTTPException: If email already exists or validation fails
    """
    user = await AuthService.create_user(db, user_data)
    return UserResponse.from_orm(user)


@router.post("/login", response_model=Token)
async def login_user(
    user_login: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Authenticate user and return access token.

    Args:
        user_login: Login credentials
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = await AuthService.authenticate_user(db, user_login)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token_data = {
        "sub": user.id,
        "email": user.email,
        "type": "access"
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user information
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user information.

    Args:
        user_data: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user information

    Raises:
        HTTPException: If validation fails
    """
    updated_user = await AuthService.update_user(db, current_user.id, user_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.from_orm(updated_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Change user password.

    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If current password is incorrect
    """
    success = await AuthService.change_password(
        db,
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[APIKeyResponse]:
    """
    Get all API keys for current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of user's API keys
    """
    api_keys = await AuthService.get_api_keys(db, current_user.id)
    return [APIKeyResponse.from_orm(api_key) for api_key in api_keys]


@router.post("/api-keys", response_model=APIKeyGenerated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeyGenerated:
    """
    Create a new API key for current user.

    Args:
        api_key_data: API key creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Generated API key (full key only shown once)
    """
    api_key, full_key = await AuthService.create_api_key(db, current_user.id, api_key_data)

    # Convert to response model and add full key
    response_data = APIKeyResponse.from_orm(api_key).dict()
    response_data["api_key"] = full_key

    return APIKeyGenerated(**response_data)


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete an API key.

    Args:
        api_key_id: API key ID to delete
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If API key not found
    """
    success = await AuthService.delete_api_key(db, current_user.id, api_key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )


@router.patch("/api-keys/{api_key_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_api_key(
    api_key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deactivate an API key.

    Args:
        api_key_id: API key ID to deactivate
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If API key not found
    """
    success = await AuthService.deactivate_api_key(db, current_user.id, api_key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
