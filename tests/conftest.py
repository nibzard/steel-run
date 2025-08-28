"""Test configuration and fixtures for Steel.run platform."""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.credential import Credential
from app.models.execution_run import ExecutionRun
from app.models.stored_action import StoredAction
from app.models.user import APIKey, User
from app.services.auth_service import AuthService
from app.utils.auth import create_access_token


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


# SQLite optimization for tests
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better test performance."""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.close()


@pytest_asyncio.fixture
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "isolation_level": None,
        },
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def sync_engine():
    """Create sync engine for testing."""
    engine = create_engine(
        TEST_SYNC_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def override_get_db(async_session):
    """Override the get_db dependency."""
    async def _override_get_db():
        yield async_session
    return _override_get_db


@pytest.fixture
def client(override_get_db):
    """Create test client with overridden database."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def async_client(override_get_db):
    """Create async test client with overridden database."""
    app.dependency_overrides[get_db] = override_get_db
    return httpx.AsyncClient(app=app, base_url="http://test")


# Password hashing
@pytest.fixture
def pwd_context():
    """Password context for testing."""
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


# Mock fixtures for external services
@pytest.fixture
def mock_steel_client():
    """Mock Steel SDK client."""
    mock = AsyncMock()
    mock.sessions.create.return_value = Mock(
        id="test_session_id",
        status="live",
        endpoint_url="https://connect.steel.dev/v1/sessions/test_session_id"
    )
    mock.sessions.release.return_value = Mock(success=True)
    mock.actions.run.return_value = Mock(
        id="test_action_run_id",
        status="completed",
        result={"success": True, "data": {"message": "Test action completed"}},
        screenshots=["https://example.com/screenshot.png"],
        logs=["Action started", "Action completed successfully"]
    )
    return mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    mock = AsyncMock()
    mock.messages.create.return_value = Mock(
        content=[Mock(text="Test AI response for action analysis")]
    )
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.set.return_value = True
    mock.get.return_value = None
    mock.delete.return_value = 1
    mock.incr.return_value = 1
    mock.expire.return_value = True
    return mock


# User fixtures
@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession, pwd_context: CryptContext) -> User:
    """Create a test user."""
    user = User(
        email="test@steel.run",
        username="testuser",
        full_name="Test User",
        hashed_password=pwd_context.hash("testpassword123"),
        is_active=True,
        is_verified=True,
        total_actions_run=5,
        default_region="lax",
        enable_screenshots=True,
        enable_webhooks=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(async_session: AsyncSession, pwd_context: CryptContext) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@steel.run",
        username="admin",
        full_name="Admin User",
        hashed_password=pwd_context.hash("adminpassword123"),
        is_active=True,
        is_verified=True,
        total_actions_run=50,
        default_region="lax",
        enable_screenshots=True,
        enable_webhooks=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(async_session: AsyncSession, pwd_context: CryptContext) -> User:
    """Create an inactive test user."""
    user = User(
        email="inactive@steel.run",
        username="inactive",
        full_name="Inactive User",
        hashed_password=pwd_context.hash("password123"),
        is_active=False,
        is_verified=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# API Key fixtures
@pytest_asyncio.fixture
async def test_api_key(async_session: AsyncSession, test_user: User) -> APIKey:
    """Create a test API key."""
    from app.utils.auth import hash_api_key
    
    raw_key = "sk_test_1234567890abcdef"
    key_hash = hash_api_key(raw_key)
    
    api_key = APIKey(
        user_id=test_user.id,
        name="Test API Key",
        key_hash=key_hash,
        key_prefix="sk_test_123",
        is_active=True,
        rate_limit_per_hour=500,
        usage_count=10,
        last_used=datetime.utcnow() - timedelta(hours=1),
    )
    async_session.add(api_key)
    await async_session.commit()
    await async_session.refresh(api_key)
    
    # Store raw key for testing
    api_key._raw_key = raw_key  # type: ignore
    return api_key


@pytest_asyncio.fixture
async def expired_api_key(async_session: AsyncSession, test_user: User) -> APIKey:
    """Create an expired test API key."""
    from app.utils.auth import hash_api_key
    
    raw_key = "sk_test_expired123"
    key_hash = hash_api_key(raw_key)
    
    api_key = APIKey(
        user_id=test_user.id,
        name="Expired API Key",
        key_hash=key_hash,
        key_prefix="sk_test_exp",
        is_active=True,
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    async_session.add(api_key)
    await async_session.commit()
    await async_session.refresh(api_key)
    
    api_key._raw_key = raw_key  # type: ignore
    return api_key


# Credential fixtures
@pytest_asyncio.fixture
async def twitter_credential(async_session: AsyncSession, test_user: User) -> Credential:
    """Create a Twitter credential."""
    credential = Credential(
        user_id=test_user.id,
        service_name="twitter",
        credential_name="Twitter Main Account",
        encrypted_data='{"username": "testuser", "password": "encrypted_password"}',
        is_active=True,
        last_validated=datetime.utcnow(),
    )
    async_session.add(credential)
    await async_session.commit()
    await async_session.refresh(credential)
    return credential


@pytest_asyncio.fixture
async def linkedin_credential(async_session: AsyncSession, test_user: User) -> Credential:
    """Create a LinkedIn credential."""
    credential = Credential(
        user_id=test_user.id,
        service_name="linkedin",
        credential_name="LinkedIn Professional",
        encrypted_data='{"email": "test@steel.run", "password": "encrypted_password"}',
        is_active=True,
        last_validated=datetime.utcnow() - timedelta(days=1),
    )
    async_session.add(credential)
    await async_session.commit()
    await async_session.refresh(credential)
    return credential


# Stored Action fixtures
@pytest_asyncio.fixture
async def twitter_stored_action(async_session: AsyncSession, test_user: User) -> StoredAction:
    """Create a Twitter stored action."""
    action = StoredAction(
        user_id=test_user.id,
        name="Daily Twitter Update",
        description="Posts daily update to Twitter",
        action_type="twitter",
        parameters=json.dumps({
            "action": "post_tweet",
            "message": "Daily update from Steel.run!",
            "include_timestamp": True,
        }),
        webhook_url="https://hooks.zapier.com/test",
        is_active=True,
        is_public=False,
        run_count=15,
        success_count=14,
        failure_count=1,
        last_run=datetime.utcnow() - timedelta(hours=2),
        last_success=datetime.utcnow() - timedelta(hours=2),
        last_failure=datetime.utcnow() - timedelta(days=5),
        avg_execution_time=3500,
        tags='["social", "automation", "daily"]',
        version=1,
    )
    async_session.add(action)
    await async_session.commit()
    await async_session.refresh(action)
    return action


@pytest_asyncio.fixture
async def linkedin_stored_action(async_session: AsyncSession, test_user: User) -> StoredAction:
    """Create a LinkedIn stored action."""
    action = StoredAction(
        user_id=test_user.id,
        name="LinkedIn Profile Update",
        description="Updates LinkedIn profile headline",
        action_type="linkedin",
        parameters=json.dumps({
            "action": "update_profile",
            "field": "headline",
            "value": "Senior Software Engineer at Steel.run",
        }),
        is_active=True,
        is_public=True,
        run_count=3,
        success_count=3,
        failure_count=0,
        last_run=datetime.utcnow() - timedelta(days=1),
        last_success=datetime.utcnow() - timedelta(days=1),
        avg_execution_time=5200,
        tags='["professional", "profile"]',
        version=2,
    )
    async_session.add(action)
    await async_session.commit()
    await async_session.refresh(action)
    return action


# Execution Run fixtures
@pytest_asyncio.fixture
async def successful_execution_run(
    async_session: AsyncSession, 
    twitter_stored_action: StoredAction
) -> ExecutionRun:
    """Create a successful execution run."""
    execution = ExecutionRun(
        stored_action_id=twitter_stored_action.id,
        user_id=twitter_stored_action.user_id,
        status="completed",
        steel_session_id="session_123",
        steel_action_run_id="run_456",
        input_parameters=json.dumps({"message": "Test tweet"}),
        result_data=json.dumps({"success": True, "tweet_id": "123456"}),
        execution_time_ms=3200,
        screenshots_urls=json.dumps(["https://example.com/screenshot.png"]),
        logs=json.dumps(["Started action", "Posted tweet", "Completed successfully"]),
        webhook_delivered=True,
        webhook_response_status=200,
        error_message=None,
    )
    async_session.add(execution)
    await async_session.commit()
    await async_session.refresh(execution)
    return execution


@pytest_asyncio.fixture
async def failed_execution_run(
    async_session: AsyncSession, 
    twitter_stored_action: StoredAction
) -> ExecutionRun:
    """Create a failed execution run."""
    execution = ExecutionRun(
        stored_action_id=twitter_stored_action.id,
        user_id=twitter_stored_action.user_id,
        status="failed",
        steel_session_id="session_789",
        steel_action_run_id="run_101",
        input_parameters=json.dumps({"message": "Test tweet"}),
        result_data=json.dumps({"success": False, "error": "Rate limit exceeded"}),
        execution_time_ms=1500,
        logs=json.dumps(["Started action", "Rate limit error", "Failed"]),
        webhook_delivered=False,
        error_message="Twitter API rate limit exceeded",
    )
    async_session.add(execution)
    await async_session.commit()
    await async_session.refresh(execution)
    return execution


# Authentication fixtures
@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authentication headers for test user."""
    token = create_access_token(data={"sub": test_user.email, "user_id": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User) -> Dict[str, str]:
    """Create authentication headers for admin user."""
    token = create_access_token(data={"sub": admin_user.email, "user_id": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_key_headers(test_api_key: APIKey) -> Dict[str, str]:
    """Create API key headers."""
    return {"X-API-Key": test_api_key._raw_key}  # type: ignore


# Test data fixtures
@pytest.fixture
def sample_action_parameters() -> Dict[str, any]:
    """Sample action parameters for testing."""
    return {
        "twitter": {
            "action": "post_tweet",
            "message": "Hello from Steel.run automation!",
            "include_timestamp": True,
        },
        "linkedin": {
            "action": "update_profile",
            "field": "headline",
            "value": "Senior Software Engineer",
        },
        "gmail": {
            "action": "send_email",
            "to": "recipient@example.com",
            "subject": "Test Email",
            "body": "This is a test email from Steel.run",
        },
        "amazon": {
            "action": "search_products",
            "query": "laptop computers",
            "price_range": {"min": 500, "max": 1500},
        },
        "website": {
            "action": "extract_data",
            "url": "https://example.com",
            "selectors": {
                "title": "h1",
                "description": ".description",
            },
        },
    }


@pytest.fixture
def mock_webhook_server():
    """Mock webhook server for testing."""
    responses = []
    
    def webhook_handler(request_data):
        responses.append(request_data)
        return {"status": "received", "timestamp": datetime.utcnow().isoformat()}
    
    return {
        "handler": webhook_handler,
        "responses": responses,
        "clear": lambda: responses.clear(),
    }


# Performance testing fixtures
@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing."""
    return {
        "users_count": 100,
        "actions_per_user": 10,
        "concurrent_requests": 50,
        "test_duration_seconds": 60,
    }


# Environment fixtures
@pytest.fixture
def test_settings():
    """Test settings configuration."""
    settings = get_settings()
    settings.testing = True
    settings.database_url = TEST_DATABASE_URL
    settings.steel_api_key = "test_steel_key"
    settings.anthropic_api_key = "test_anthropic_key"
    settings.redis_url = "redis://localhost:6379/1"
    settings.secret_key = "test_secret_key_for_testing_only"
    return settings


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "STEEL_API_KEY": "test_steel_key",
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "DATABASE_URL": TEST_DATABASE_URL,
        "SECRET_KEY": "test_secret_key",
        "REDIS_URL": "redis://localhost:6379/1",
        "ENVIRONMENT": "test",
    }):
        yield


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Any cleanup code can go here
    pass


# Custom assertions and utilities
@pytest.fixture
def assert_api_response():
    """Utility for asserting API response structure."""
    def _assert_response(response, expected_status=200, expected_keys=None):
        assert response.status_code == expected_status
        if expected_keys:
            data = response.json()
            for key in expected_keys:
                assert key in data
        return response.json()
    return _assert_response


@pytest.fixture
def create_test_users():
    """Factory for creating multiple test users."""
    async def _create_users(session: AsyncSession, count: int = 10) -> List[User]:
        users = []
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        for i in range(count):
            user = User(
                email=f"user{i}@test.com",
                username=f"user{i}",
                full_name=f"Test User {i}",
                hashed_password=pwd_context.hash("password123"),
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            users.append(user)
        
        await session.commit()
        return users
    return _create_users


# Mark fixtures for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
pytest.mark.api = pytest.mark.api
pytest.mark.actions = pytest.mark.actions