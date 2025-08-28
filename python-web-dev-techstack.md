# Modern Python Web Development Tech Stack - Development Team Specification

## Executive Summary

This specification outlines the recommended modern, robust, and production-ready technology stack for building web services, web applications, backends, and frontends using Python. The stack emphasizes performance, security, maintainability, and developer experience while leveraging cutting-edge tools and best practices.

## 1. Core Development Tools

### 1.1 Python Package and Project Management

**Primary Tool: uv (by Astral)**
- **Version**: Latest stable (2025+)
- **Purpose**: All-in-one Python package and project manager
- **Key Features**:
  - 10-100x faster than pip for package installation
  - Replaces pip, pip-tools, pipx, poetry, pyenv, virtualenv, and twine
  - Built in Rust for exceptional performance
  - Automatic virtual environment management
  - Python version management (like pyenv)
  - Lock file generation for reproducible builds
  - Global cache for efficient disk usage

**Installation**:
```bash
# Standalone (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows
```

**Project Initialization**:
```bash
uv init my-project
cd my-project
uv add fastapi uvicorn
uv run main.py
```

### 1.2 Code Quality and Formatting

**Primary Tool: Ruff (by Astral)**
- **Purpose**: Blazingly fast Python linter and formatter
- **Features**: Replaces black, autoflake, isort, and supports 600+ lint rules
- **Integration**: Pre-commit hooks and CI/CD pipelines

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
select = ["E", "F", "B", "I", "N", "UP"]
fix = true
```

## 2. Web Framework Stack

### 2.1 Backend Framework

**Primary Framework: FastAPI**
- **Version**: Latest stable (0.100+)
- **Key Features**:
  - High performance (comparable to NodeJS and Go)
  - Automatic OpenAPI documentation generation
  - Built-in type safety with Pydantic
  - Async/await support out of the box
  - Excellent developer experience

**Alternative Framework: Django (for specific use cases)**
- **Use Cases**: Complex business logic, built-in admin, ORM-heavy applications
- **Version**: Latest LTS

### 2.2 ASGI Server

**Production Server: Gunicorn with Uvicorn Workers**
```bash
# Production deployment
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Development Server: Uvicorn**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 3. Data Layer and Persistence

### 3.1 Object-Relational Mapping (ORM)

**Primary ORM: SQLAlchemy 2.0+**
- **Features**:
  - Core and ORM layers for flexibility
  - Async support for modern applications
  - Type safety improvements
  - Performance optimizations
  - Migration support via Alembic

**Database Migration Tool: Alembic**
```bash
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 3.2 Database Recommendations

**Primary Database: PostgreSQL**
- **Use Cases**: Most production applications
- **Features**: ACID compliance, JSON support, full-text search

**Alternative Databases**:
- **SQLite**: Development and small applications

### 3.3 Caching Layer

**Primary Cache: Redis**
- **Use Cases**: Session storage, API response caching, real-time features
- **Python Client**: redis-py with asyncio support
- **Features**: Pub/Sub, streams, advanced data structures

```python
# Redis caching example
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

# Cache with expiration
def cache_response(key: str, data: dict, expire_seconds: int = 3600):
    r.setex(key, expire_seconds, json.dumps(data))

# Retrieve from cache
def get_cached_response(key: str):
    cached = r.get(key)
    return json.loads(cached) if cached else None
```

## 4. Data Validation and Serialization

### 4.1 Data Validation

**Primary Tool: Pydantic V2**
- **Features**: Type-based validation, JSON Schema generation, performance improvements
- **Integration**: Native FastAPI integration

```python
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8)
    age: Optional[int] = Field(gt=0, le=150)

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True
```

## 5. Authentication and Security

### 5.1 Authentication Strategy

**Primary Method: JWT (JSON Web Tokens)**
- **Library**: PyJWT
- **Features**: Stateless authentication, cross-domain compatibility, scalable

```python
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### 5.2 Security Best Practices

**Password Hashing**: bcrypt via passlib
**HTTPS**: Always use TLS in production
**CORS**: Configure appropriately for frontend integration
**Input Validation**: Leverage Pydantic for all input validation
**SQL Injection Prevention**: Use SQLAlchemy's parameterized queries

## 6. Testing Framework

### 6.1 Primary Testing Tool

**Framework: pytest**
- **Features**: Simple syntax, powerful fixtures, extensive plugin ecosystem
- **Async Support**: pytest-asyncio for async tests
- **API Testing**: httpx for FastAPI integration

```python
# pytest configuration
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/users/",
            json={"email": "test@example.com", "name": "Test User", "password": "testpass123"}
        )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

### 6.2 Testing Coverage

**Coverage Tool**: pytest-cov
**Target**: Minimum 80% code coverage for production applications

## 7. Logging and Monitoring

### 7.1 Structured Logging

**Primary Tool: structlog**
- **Features**: Structured logging, JSON output, context preservation
- **Production**: JSON format for log aggregation
- **Development**: Pretty printing for readability

```python
import structlog

# Configuration
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Usage
logger.info("User created", user_id=123, email="user@example.com")
```

### 7.2 Application Monitoring

**Metrics Collection: Prometheus**
- **Client Library**: prometheus_client
- **Custom Metrics**: Request duration, error rates, business metrics

**Visualization: Grafana**
- **Dashboards**: Application performance, system metrics
- **Alerting**: Proactive issue detection

```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)

    return response
```

## 8. Containerization and Deployment

### 8.1 Containerization

**Container Platform: Docker**
- **Base Image**: python:3.12-slim for production
- **Multi-stage builds**: Optimize image size and security

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 10. CI/CD Pipeline

### 10.1 Continuous Integration

**Platform: GitHub Actions**
- **Features**: Native GitHub integration, Docker support, secret management

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Setup Python
      run: uv python install 3.12

    - name: Install dependencies
      run: uv sync

    - name: Run tests
      run: uv run pytest --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v4

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        push: true
        tags: ${{ secrets.REGISTRY }}/app:${{ github.sha }}
```

## 11. Project Structure

### 11.1 Recommended Directory Layout

```
my-project/
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Configuration settings
│       │   ├── security.py      # Authentication/authorization
│       │   └── database.py      # Database connection
│       ├── api/
│       │   ├── __init__.py
│       │   ├── dependencies.py  # FastAPI dependencies
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── endpoints/
│       │       │   ├── __init__.py
│       │       │   ├── users.py
│       │       │   └── auth.py
│       │       └── api.py       # API router
│       ├── models/
│       │   ├── __init__.py
│       │   ├── user.py         # SQLAlchemy models
│       │   └── base.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── user.py         # Pydantic models
│       │   └── base.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── user_service.py # Business logic
│       │   └── auth_service.py
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_users.py
│   └── test_auth.py
├── migrations/                 # Alembic migrations
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── uv.lock
├── README.md
└── .env.example
```

### 11.2 Configuration Management

```python
# core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "FastAPI App"
    debug: bool = False
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## 12. Frontend Integration (Optional)

### 12.1 API-First Approach

**Strategy**: Separate frontend and backend applications
**Communication**: RESTful APIs with JSON
**Documentation**: Automatic OpenAPI/Swagger documentation via FastAPI

### 12.2 Frontend Framework Recommendations

**Modern SPA**: React, Vue.js, or Angular
**Python-based**: Reflex (full-stack Python) for internal tools
**Static Sites**: Next.js, Nuxt.js for marketing sites

## 13. Performance Optimization

### 13.1 Caching Strategy

**Application Level**: Redis for session and API response caching
**Database Level**: Query optimization, connection pooling
**HTTP Level**: Nginx caching, CDN integration

### 13.2 Async Best Practices

**Database**: Use async SQLAlchemy and asyncpg
**HTTP Requests**: Use httpx for external API calls
**Background Tasks**: Celery with Redis broker

## 14. Security Checklist

- [ ] Use HTTPS in production
- [ ] Implement proper CORS policies
- [ ] Validate all input with Pydantic
- [ ] Use parameterized database queries
- [ ] Implement rate limiting
- [ ] Use secure session management
- [ ] Regular dependency updates
- [ ] Security headers (helmet equivalent)
- [ ] Environment variable management
- [ ] Secrets rotation strategy

## 15. Production Readiness Checklist

### 15.1 Application Requirements

- [ ] Comprehensive error handling
- [ ] Structured logging implementation
- [ ] Health check endpoints
- [ ] Graceful shutdown handling
- [ ] Database connection pooling
- [ ] Async/await throughout the stack
- [ ] Input validation and sanitization
- [ ] API rate limiting
- [ ] Monitoring and metrics collection

### 15.2 Infrastructure Requirements

- [ ] Load balancing (Nginx/HAProxy)
- [ ] Database replication and backups
- [ ] Redis clustering for high availability
- [ ] SSL/TLS certificates
- [ ] Log aggregation (ELK stack or similar)
- [ ] Monitoring dashboards (Grafana)
- [ ] Alerting system (Prometheus AlertManager)
- [ ] CI/CD pipeline implementation

---

**Document Version**: 1.0
**Last Updated**: August 28, 2025
**Review Cycle**: Quarterly