"""Main API v1 router combining all endpoints."""

from fastapi import APIRouter

from . import (
    action_templates,
    actions,
    auth,
    bulk_operations,
    credentials,
    monitoring,
    stored_actions,
    websocket,
)

# Create the main API router
api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# Include action discovery and execution endpoints
api_router.include_router(
    actions.router,
    prefix="/actions",
    tags=["Actions"],
)

# Include stored actions endpoints
api_router.include_router(
    stored_actions.router,
    prefix="/stored-actions",
    tags=["Stored Actions"],
)

# Include credential management endpoints
api_router.include_router(
    credentials.router,
    prefix="/credentials",
    tags=["Credentials"],
)

# Include monitoring endpoints
api_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["Monitoring"],
)

# Include WebSocket endpoints
api_router.include_router(
    websocket.router,
    prefix="/ws",
    tags=["WebSocket"],
)

# Include bulk operations endpoints
api_router.include_router(
    bulk_operations.router,
    prefix="/bulk",
    tags=["Bulk Operations"],
)

# Include action templates endpoints
api_router.include_router(
    action_templates.router,
    prefix="/templates",
    tags=["Action Templates"],
)
