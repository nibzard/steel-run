"""Monitoring and health check API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ...core.config import settings
from ...services.monitoring_service import monitoring_service

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns detailed health status including database connectivity,
    external services, and performance metrics.
    """
    try:
        health_status = await monitoring_service.get_health_status()

        # Return appropriate HTTP status based on health
        if health_status["status"] == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status
            )

        return health_status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Health check failed",
                "error": str(e)
            }
        )


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """
    Kubernetes/load balancer readiness probe.

    Returns simple ready/not ready status for traffic routing decisions.
    """
    try:
        readiness_status = await monitoring_service.get_readiness_status()

        if readiness_status["status"] == "not_ready":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=readiness_status
            )

        return readiness_status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Readiness check failed",
                "error": str(e)
            }
        )


@router.get("/live")
async def liveness_check() -> dict[str, Any]:
    """
    Kubernetes liveness probe.

    Simple check to verify the application is running and responsive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
    }


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    if not settings.enable_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics are disabled"
        )

    try:
        # Trigger metrics collection to ensure fresh data
        await monitoring_service.get_detailed_metrics()

        # Generate Prometheus metrics
        metrics_data = generate_latest()

        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate metrics: {str(e)}"
        )


@router.get("/metrics/detailed")
async def detailed_metrics() -> dict[str, Any]:
    """
    Detailed application metrics in JSON format.

    Provides comprehensive metrics for monitoring dashboards
    and debugging purposes.
    """
    try:
        metrics = await monitoring_service.get_detailed_metrics()
        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to collect detailed metrics",
                "message": str(e)
            }
        )


@router.get("/status")
async def application_status() -> dict[str, Any]:
    """
    Application status overview.

    Combines health check and key metrics for a status page.
    """
    try:
        # Get health status
        health = await monitoring_service.get_health_status()

        # Get key metrics
        detailed_metrics = await monitoring_service.get_detailed_metrics()

        return {
            "overall_status": health["status"],
            "timestamp": health["timestamp"],
            "version": settings.version,
            "environment": settings.env,
            "health_checks": health["checks"],
            "key_metrics": {
                "total_users": detailed_metrics.get("application", {}).get("total_users", 0),
                "active_users_24h": detailed_metrics.get("application", {}).get("active_users_24h", 0),
                "total_executions": detailed_metrics.get("application", {}).get("total_executions", 0),
                "success_rate_24h": detailed_metrics.get("business", {}).get("success_rate_24h", 0),
                "database_response_time": detailed_metrics.get("performance", {}).get("database_response_time", 0),
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to get application status",
                "message": str(e)
            }
        )


@router.post("/metrics/reset")
async def reset_metrics() -> dict[str, str]:
    """
    Reset metrics counters (development/testing only).

    Only available when debug mode is enabled.
    """
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics reset only available in debug mode"
        )

    try:
        # Clear metrics cache
        monitoring_service._metrics_cache.clear()
        monitoring_service._last_metrics_update = 0

        return {
            "status": "success",
            "message": "Metrics cache cleared"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset metrics: {str(e)}"
        )


@router.get("/debug/config")
async def debug_configuration() -> dict[str, Any]:
    """
    Debug endpoint showing sanitized configuration.

    Only available when debug mode is enabled.
    """
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoints only available in debug mode"
        )

    # Return sanitized configuration (no secrets)
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.env,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "database_url": "***REDACTED***",
        "enable_metrics": settings.enable_metrics,
        "log_level": settings.log_level,
        "cors_origins": settings.cors_origins,
        "rate_limit_per_ip": settings.rate_limit_per_ip,
        "rate_limit_per_user": settings.rate_limit_per_user,
        "enable_rate_limiting": settings.enable_rate_limiting,
    }
