"""Credential service for secure storage and management."""

import json
from datetime import datetime
from typing import Any

import structlog
from cryptography.fernet import Fernet
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.credential import Credential, CredentialType
from ..schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialUsageStats,
    CredentialValidationResponse,
)

logger = structlog.get_logger(__name__)


class CredentialEncryptionService:
    """Service for encrypting and decrypting credential data."""

    def __init__(self):
        """Initialize the encryption service with Fernet cipher."""
        self._fernet = Fernet(settings.credential_encryption_key.encode())

    def encrypt(self, data: dict[str, Any]) -> str:
        """Encrypt credential data."""
        try:
            json_data = json.dumps(data, default=str).encode()
            encrypted_data = self._fernet.encrypt(json_data)
            return encrypted_data.decode()
        except Exception as e:
            logger.error("Failed to encrypt credential data", error=str(e))
            raise ValueError("Failed to encrypt credential data")

    def decrypt(self, encrypted_data: str) -> dict[str, Any]:
        """Decrypt credential data."""
        try:
            decrypted_data = self._fernet.decrypt(encrypted_data.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error("Failed to decrypt credential data", error=str(e))
            raise ValueError("Failed to decrypt credential data")


class CredentialService:
    """Service for managing user credentials."""

    def __init__(self):
        """Initialize credential service."""
        self._encryption_service = CredentialEncryptionService()

    async def create_credential(
        self,
        db: AsyncSession,
        user_id: str,
        credential_data: CredentialCreate
    ) -> Credential:
        """Create a new encrypted credential."""
        try:
            # Encrypt the credential data
            encrypted_data = self._encryption_service.encrypt(credential_data.credential_data)

            # Create credential record
            credential = Credential(
                user_id=user_id,
                name=credential_data.name,
                domain=credential_data.domain.lower(),  # Normalize domain
                credential_type=credential_data.credential_type.value,
                encrypted_data=encrypted_data,
                description=credential_data.description,
                expires_at=credential_data.expires_at,
                tags=json.dumps(credential_data.tags) if credential_data.tags else None,
                access_restricted_to_actions=json.dumps(credential_data.access_restricted_to_actions)
                if credential_data.access_restricted_to_actions else None,
            )

            db.add(credential)
            await db.commit()
            await db.refresh(credential)

            logger.info(
                "Created new credential",
                credential_id=credential.id,
                user_id=user_id,
                domain=credential.domain,
                type=credential.credential_type,
            )

            return credential

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create credential", error=str(e), user_id=user_id)
            raise

    async def get_credential(
        self,
        db: AsyncSession,
        credential_id: str,
        user_id: str
    ) -> Credential | None:
        """Get a credential by ID for a specific user."""
        result = await db.execute(
            select(Credential).where(
                and_(Credential.id == credential_id, Credential.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_credential_with_data(
        self,
        db: AsyncSession,
        credential_id: str,
        user_id: str
    ) -> tuple[Credential, dict[str, Any]] | None:
        """Get a credential with decrypted data."""
        credential = await self.get_credential(db, credential_id, user_id)
        if not credential:
            return None

        if not credential.is_valid:
            logger.warning(
                "Attempted to access invalid credential",
                credential_id=credential_id,
                is_active=credential.is_active,
                is_expired=credential.is_expired,
            )
            return None

        try:
            decrypted_data = self._encryption_service.decrypt(credential.encrypted_data)
            return credential, decrypted_data
        except Exception as e:
            logger.error("Failed to decrypt credential", credential_id=credential_id, error=str(e))
            return None

    async def list_credentials(
        self,
        db: AsyncSession,
        user_id: str,
        domain: str | None = None,
        credential_type: CredentialType | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Credential]:
        """List user credentials with optional filtering."""
        query = select(Credential).where(Credential.user_id == user_id)

        if domain:
            query = query.where(Credential.domain == domain.lower())

        if credential_type:
            query = query.where(Credential.credential_type == credential_type.value)

        if tags:
            # Filter by tags (this is a simple contains check, could be improved)
            for tag in tags:
                query = query.where(Credential.tags.contains(f'"{tag}"'))

        query = query.offset(skip).limit(limit).order_by(Credential.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def list_credentials_for_domain(
        self,
        db: AsyncSession,
        user_id: str,
        domain: str,
        action_id: str | None = None,
    ) -> list[Credential]:
        """List valid credentials for a specific domain, optionally filtered by action access."""
        query = select(Credential).where(
            and_(
                Credential.user_id == user_id,
                Credential.domain == domain.lower(),
                Credential.is_active == True,  # noqa: E712
            )
        )

        result = await db.execute(query)
        credentials = list(result.scalars().all())

        # Filter out expired credentials and check action access
        valid_credentials = []
        for cred in credentials:
            if cred.is_expired:
                continue

            if action_id and not cred.can_be_used_by_action(action_id):
                continue

            valid_credentials.append(cred)

        return valid_credentials

    async def update_credential(
        self,
        db: AsyncSession,
        credential_id: str,
        user_id: str,
        credential_data: CredentialUpdate
    ) -> Credential | None:
        """Update a credential."""
        credential = await self.get_credential(db, credential_id, user_id)
        if not credential:
            return None

        try:
            # Update basic fields
            if credential_data.name is not None:
                credential.name = credential_data.name
            if credential_data.description is not None:
                credential.description = credential_data.description
            if credential_data.expires_at is not None:
                credential.expires_at = credential_data.expires_at
            if credential_data.is_active is not None:
                credential.is_active = credential_data.is_active
            if credential_data.tags is not None:
                credential.tags = json.dumps(credential_data.tags) if credential_data.tags else None
            if credential_data.access_restricted_to_actions is not None:
                credential.access_restricted_to_actions = (
                    json.dumps(credential_data.access_restricted_to_actions)
                    if credential_data.access_restricted_to_actions else None
                )

            # Update encrypted data if provided
            if credential_data.credential_data is not None:
                encrypted_data = self._encryption_service.encrypt(credential_data.credential_data)
                credential.encrypted_data = encrypted_data
                credential.last_validated = None  # Reset validation status
                credential.validation_status = None

            credential.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(credential)

            logger.info("Updated credential", credential_id=credential_id, user_id=user_id)
            return credential

        except Exception as e:
            await db.rollback()
            logger.error("Failed to update credential", error=str(e), credential_id=credential_id)
            raise

    async def delete_credential(
        self,
        db: AsyncSession,
        credential_id: str,
        user_id: str
    ) -> bool:
        """Delete a credential."""
        credential = await self.get_credential(db, credential_id, user_id)
        if not credential:
            return False

        try:
            await db.delete(credential)
            await db.commit()

            logger.info("Deleted credential", credential_id=credential_id, user_id=user_id)
            return True

        except Exception as e:
            await db.rollback()
            logger.error("Failed to delete credential", error=str(e), credential_id=credential_id)
            raise

    async def validate_credential(
        self,
        db: AsyncSession,
        credential_id: str,
        user_id: str,
        validation_url: str | None = None,
    ) -> CredentialValidationResponse:
        """Validate a credential by testing it."""
        credential_data = await self.get_credential_with_data(db, credential_id, user_id)
        if not credential_data:
            return CredentialValidationResponse(
                credential_id=credential_id,
                is_valid=False,
                validation_message="Credential not found or invalid",
                validated_at=datetime.utcnow(),
            )

        credential, decrypted_data = credential_data

        try:
            # Basic validation - check if credential has required fields
            is_valid = await self._validate_credential_structure(credential, decrypted_data)

            if is_valid and validation_url:
                # TODO: Implement actual credential testing against validation_url
                # This would involve making HTTP requests to test the credential
                logger.info("URL-based credential validation not yet implemented")

            # Update credential validation status
            credential.last_validated = datetime.utcnow()
            credential.validation_status = "valid" if is_valid else "invalid"
            await db.commit()

            return CredentialValidationResponse(
                credential_id=credential_id,
                is_valid=is_valid,
                validation_message="Credential structure is valid" if is_valid else "Invalid credential structure",
                validated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error("Failed to validate credential", credential_id=credential_id, error=str(e))
            return CredentialValidationResponse(
                credential_id=credential_id,
                is_valid=False,
                validation_message=f"Validation failed: {str(e)}",
                validated_at=datetime.utcnow(),
            )

    async def _validate_credential_structure(self, credential: Credential, data: dict[str, Any]) -> bool:
        """Validate credential data structure based on type."""
        try:
            cred_type = CredentialType(credential.credential_type)

            if cred_type == CredentialType.USERNAME_PASSWORD:
                return "username" in data and "password" in data and data["username"] and data["password"]

            elif cred_type == CredentialType.API_KEY:
                return "api_key" in data and data["api_key"]

            elif cred_type == CredentialType.OAUTH_TOKEN:
                return "access_token" in data and data["access_token"]

            elif cred_type == CredentialType.BEARER_TOKEN:
                return "token" in data and data["token"]

            elif cred_type == CredentialType.COOKIE_SESSION:
                return "cookies" in data and data["cookies"]

            # CUSTOM type is always considered structurally valid
            return True

        except Exception:
            return False

    async def record_credential_usage(
        self,
        db: AsyncSession,
        credential_id: str,
        success: bool = True,
    ) -> None:
        """Record credential usage for tracking."""
        try:
            credential = await db.get(Credential, credential_id)
            if credential:
                credential.usage_count += 1
                credential.last_used = datetime.utcnow()

                # Update validation status if this was a successful use
                if success and credential.validation_status != "valid":
                    credential.validation_status = "valid"
                    credential.last_validated = datetime.utcnow()

                await db.commit()

        except Exception as e:
            logger.warning("Failed to record credential usage", credential_id=credential_id, error=str(e))
            # Don't fail the main operation if usage tracking fails

    async def get_credential_usage_stats(
        self,
        db: AsyncSession,
        user_id: str,
        credential_id: str | None = None,
    ) -> list[CredentialUsageStats]:
        """Get usage statistics for credentials."""
        query = select(Credential).where(Credential.user_id == user_id)

        if credential_id:
            query = query.where(Credential.id == credential_id)

        result = await db.execute(query)
        credentials = result.scalars().all()

        stats = []
        for cred in credentials:
            stats.append(
                CredentialUsageStats(
                    credential_id=cred.id,
                    usage_count=cred.usage_count,
                    last_used=cred.last_used,
                    success_rate=1.0 if cred.validation_status == "valid" else 0.0,  # Simplified
                    avg_response_time=None,  # TODO: Implement response time tracking
                    recent_errors=[],  # TODO: Implement error tracking
                )
            )

        return stats
