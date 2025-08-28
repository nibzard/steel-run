"""Authentication service for user management and API keys."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import APIKey, User
from ..schemas.auth import APIKeyCreate, UserCreate, UserLogin, UserUpdate
from ..utils.auth import generate_api_key, get_password_hash, verify_password


class AuthService:
    """Service class for authentication operations."""

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            db: Database session
            user_data: User creation data

        Returns:
            Created user instance

        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Check username if provided
        if user_data.username:
            result = await db.execute(select(User).where(User.username == user_data.username))
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            default_region=user_data.default_region,
            enable_screenshots=user_data.enable_screenshots,
            enable_webhooks=user_data.enable_webhooks,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, user_login: UserLogin) -> User | None:
        """
        Authenticate a user by email and password.

        Args:
            db: Database session
            user_login: Login credentials

        Returns:
            User instance if authentication successful, None otherwise
        """
        result = await db.execute(select(User).where(User.email == user_login.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(user_login.password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User instance if found, None otherwise
        """
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """
        Get user by email.

        Args:
            db: Database session
            email: User email

        Returns:
            User instance if found, None otherwise
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: str, user_data: UserUpdate) -> User | None:
        """
        Update user information.

        Args:
            db: Database session
            user_id: User ID
            user_data: Update data

        Returns:
            Updated user instance if found, None otherwise

        Raises:
            HTTPException: If username already taken
        """
        user = await AuthService.get_user_by_id(db, user_id)
        if not user:
            return None

        # Check username if being updated
        if user_data.username and user_data.username != user.username:
            result = await db.execute(select(User).where(User.username == user_data.username))
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def change_password(db: AsyncSession, user_id: str, current_password: str, new_password: str) -> bool:
        """
        Change user password.

        Args:
            db: Database session
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully, False otherwise
        """
        user = await AuthService.get_user_by_id(db, user_id)
        if not user:
            return False

        if not verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = get_password_hash(new_password)
        await db.commit()

        return True

    @staticmethod
    async def create_api_key(db: AsyncSession, user_id: str, api_key_data: APIKeyCreate) -> tuple[APIKey, str]:
        """
        Create a new API key for a user.

        Args:
            db: Database session
            user_id: User ID
            api_key_data: API key creation data

        Returns:
            Tuple of (APIKey instance, full API key string)
        """
        # Generate API key
        full_key, key_prefix, key_hash = generate_api_key()

        # Create API key record
        api_key = APIKey(
            user_id=user_id,
            name=api_key_data.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            rate_limit_per_hour=api_key_data.rate_limit_per_hour,
            expires_at=api_key_data.expires_at,
        )

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        return api_key, full_key

    @staticmethod
    async def get_api_keys(db: AsyncSession, user_id: str) -> list[APIKey]:
        """
        Get all API keys for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of API key instances
        """
        result = await db.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_api_key_by_id(db: AsyncSession, user_id: str, api_key_id: str) -> APIKey | None:
        """
        Get API key by ID for a specific user.

        Args:
            db: Database session
            user_id: User ID
            api_key_id: API key ID

        Returns:
            API key instance if found, None otherwise
        """
        result = await db.execute(
            select(APIKey)
            .where(APIKey.id == api_key_id, APIKey.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def verify_api_key(db: AsyncSession, api_key: str) -> User | None:
        """
        Verify an API key and return associated user.

        Args:
            db: Database session
            api_key: API key to verify

        Returns:
            User instance if API key is valid, None otherwise
        """
        from ..utils.auth import verify_api_key as verify_key_hash

        # Get key prefix
        key_prefix = api_key[:12] if len(api_key) >= 12 else api_key

        # Find API key by prefix
        result = await db.execute(
            select(APIKey)
            .where(APIKey.key_prefix == key_prefix, APIKey.is_active)
        )

        api_key_record = result.scalar_one_or_none()
        if not api_key_record or not api_key_record.is_valid:
            return None

        # Verify hash
        if not verify_key_hash(api_key, api_key_record.key_hash):
            return None

        # Update usage statistics
        api_key_record.last_used = datetime.utcnow()
        api_key_record.usage_count += 1
        await db.commit()

        # Get associated user
        return await AuthService.get_user_by_id(db, api_key_record.user_id)

    @staticmethod
    async def deactivate_api_key(db: AsyncSession, user_id: str, api_key_id: str) -> bool:
        """
        Deactivate an API key.

        Args:
            db: Database session
            user_id: User ID
            api_key_id: API key ID

        Returns:
            True if deactivated successfully, False otherwise
        """
        api_key = await AuthService.get_api_key_by_id(db, user_id, api_key_id)
        if not api_key:
            return False

        api_key.is_active = False
        await db.commit()

        return True

    @staticmethod
    async def delete_api_key(db: AsyncSession, user_id: str, api_key_id: str) -> bool:
        """
        Delete an API key.

        Args:
            db: Database session
            user_id: User ID
            api_key_id: API key ID

        Returns:
            True if deleted successfully, False otherwise
        """
        api_key = await AuthService.get_api_key_by_id(db, user_id, api_key_id)
        if not api_key:
            return False

        await db.delete(api_key)
        await db.commit()

        return True
