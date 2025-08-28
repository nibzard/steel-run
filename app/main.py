"""
Steel.run FastAPI Application

Atomic Web Functions Platform - Transform natural language into web actions.
"""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import REGISTRY, Counter, Histogram

from .core.config import settings
from .core.database import check_connection, create_tables

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Clear any existing metrics to avoid conflicts
try:
    REGISTRY.unregister(REGISTRY._names_to_collectors.get('steel_http_requests_total'))
    REGISTRY.unregister(REGISTRY._names_to_collectors.get('steel_http_request_duration_seconds'))
    REGISTRY.unregister(REGISTRY._names_to_collectors.get('steel_active_sessions_total'))
except (KeyError, AttributeError):
    pass

# Prometheus metrics
REQUEST_COUNT = Counter(
    'steel_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)
REQUEST_DURATION = Histogram(
    'steel_http_request_duration_seconds',
    'HTTP request duration in seconds'
)
ACTIVE_SESSIONS = Counter(
    'steel_active_sessions_total',
    'Total active Steel browser sessions'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Steel.run application")

    # Setup graceful shutdown handling
    from .core.shutdown import shutdown_handler
    shutdown_handler.setup_signal_handlers()

    # Create database tables
    try:
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise

    # Check database connection
    if not await check_connection():
        logger.error("Database connection failed")
        raise RuntimeError("Database connection failed")

    # Initialize actions
    try:
        from .actions.bootstrap import initialize_actions
        initialize_actions()
        logger.info("Actions initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize actions", error=str(e))
        # Don't fail startup if actions can't be initialized

    logger.info("Application startup complete")

    yield

    logger.info("Shutting down Steel.run application")
    # Graceful shutdown will be handled by the shutdown handler


# Create FastAPI application
app = FastAPI(
    title="Steel.run API",
    description="Atomic Web Functions Platform - Transform natural language into web actions",
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Security middleware (order matters - apply from outside in)
from .middleware.security import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    RateLimitSecurityMiddleware,
    InputSanitizationMiddleware,
    CORSSecurityMiddleware,
)
from .middleware.rate_limit import RateLimitMiddleware

# Apply security middleware in the correct order
app.add_middleware(SecurityHeadersMiddleware)  # Outermost - adds security headers
app.add_middleware(RequestLoggingMiddleware)   # Log security events
# Disabled for development - enable in production
# app.add_middleware(RateLimitSecurityMiddleware)  # Enhanced rate limiting
app.add_middleware(InputSanitizationMiddleware)  # Input validation
# app.add_middleware(RateLimitMiddleware)        # General rate limiting
app.add_middleware(CORSSecurityMiddleware)     # Secure CORS handling

# Fallback CORS middleware for compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect request metrics."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    REQUEST_DURATION.observe(duration)

    return response


# Mount static files
try:
    app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")
except RuntimeError:
    # Directory might not exist in development
    logger.warning("Static files directory not found")

# Setup templates
try:
    templates = Jinja2Templates(directory="app/frontend/templates")
except Exception:
    # Templates might not exist yet
    logger.warning("Templates directory not found")
    templates = None


# Enhanced health check endpoints (replaced by monitoring service)
# The monitoring service provides more comprehensive health checks


# Frontend routes (will be implemented by Frontend Agent)
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page with natural language input."""
    if templates is None:
        return HTMLResponse("""
        <html>
            <head><title>Steel.run</title></head>
            <body>
                <h1>Steel.run - Atomic Web Functions</h1>
                <p>Frontend templates not yet implemented.</p>
                <p>API documentation available at <a href="/docs">/docs</a></p>
            </body>
        </html>
        """)

    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard with action gallery."""
    if templates is None:
        return HTMLResponse("<h1>Dashboard - Coming Soon</h1>")

    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/editor", response_class=HTMLResponse)
async def editor(request: Request):
    """Code editor and action preview."""
    if templates is None:
        return HTMLResponse("<h1>Editor - Coming Soon</h1>")

    return templates.TemplateResponse("editor.html", {"request": request})


@app.get("/my-actions", response_class=HTMLResponse)
async def my_actions(request: Request):
    """User's saved actions management."""
    if templates is None:
        return HTMLResponse("<h1>My Actions - Coming Soon</h1>")

    return templates.TemplateResponse("my_actions.html", {"request": request})


# API routes
from .api.v1.api import api_router

app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
        log_level=settings.log_level.lower(),
    )
