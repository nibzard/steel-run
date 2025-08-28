"""API dependencies for authentication and database access."""


from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..models.user import User
from ..services.auth_service import AuthService
from ..utils.auth import verify_token

# Security scheme for JWT tokens
bearer_scheme = HTTPBearer()

# Security scheme for API keys (optional)
api_key_header = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: Authorization credentials
        db: Database session

    Returns:
        Current user instance

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify JWT token
        payload = verify_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Get user from database
    user = await AuthService.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get current authenticated user from JWT token (optional).

    Args:
        credentials: Optional authorization credentials
        db: Database session

    Returns:
        Current user instance if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (same as get_current_user, but more explicit).

    Args:
        current_user: Current user from JWT token

    Returns:
        Current active user instance
    """
    return current_user


async def get_user_from_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get user from API key authentication.

    Args:
        request: HTTP request
        db: Database session

    Returns:
        User instance if API key is valid, None otherwise
    """
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    # Verify API key
    user = await AuthService.verify_api_key(db, api_key)

    return user


async def get_current_user_or_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from either JWT token or API key.

    Args:
        request: HTTP request
        credentials: Optional authorization credentials
        db: Database session

    Returns:
        Current user instance

    Raises:
        HTTPException: If neither authentication method is valid
    """
    # Try JWT token first
    if credentials:
        try:
            return await get_current_user(credentials, db)
        except HTTPException:
            pass

    # Try API key
    user = await get_user_from_api_key(request, db)
    if user:
        return user

    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Use either JWT token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_or_api_key_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get current user from either JWT token or API key (optional).

    Args:
        request: HTTP request
        credentials: Optional authorization credentials
        db: Database session

    Returns:
        Current user instance if authenticated, None otherwise
    """
    try:
        return await get_current_user_or_api_key(request, credentials, db)
    except HTTPException:
        return None


def require_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require user to be verified.

    Args:
        current_user: Current user

    Returns:
        Verified user instance

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not verified"
        )

    return current_user


def require_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require user to be admin (placeholder for future role system).

    Args:
        current_user: Current user

    Returns:
        Admin user instance

    Raises:
        HTTPException: If user is not admin
    """
    # For now, check if user email ends with @steel.run
    if not current_user.email.endswith("@steel.run"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def get_websocket_user(websocket: WebSocket) -> User | None:
    """
    Get user from WebSocket connection.

    Extracts authentication token from query parameters or headers
    and validates the user.

    Args:
        websocket: WebSocket connection

    Returns:
        User instance if authenticated, None otherwise
    """
    # Try to get token from query parameters
    token = websocket.query_params.get("token")

    # If not in query params, try headers (if available)
    if not token and hasattr(websocket, "headers"):
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    try:
        # Verify JWT token
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        # Get user from database
        from ..core.database import get_db_session
        async with get_db_session() as db:
            user = await AuthService.get_user_by_id(db, user_id)
            if user and user.is_active:
                return user

        return None

    except Exception:
        return None
