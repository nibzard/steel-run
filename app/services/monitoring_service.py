"""Monitoring and observability service."""

import time
from datetime import datetime, timedelta
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram, Info
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db_session
from ..models.execution_run import ExecutionRun
from ..models.stored_action import StoredAction
from ..models.user import User

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Prometheus metrics collection."""

    def __init__(self):
        """Initialize metrics collectors."""
        # Application info
        self.app_info = Info('steel_app', 'Application information')
        self.app_info.info({
            'version': settings.version,
            'environment': settings.env,
        })

        # Request metrics (already defined in main.py, but adding more detailed ones)
        self.action_executions_total = Counter(
            'steel_action_executions_total',
            'Total action executions',
            ['action_type', 'status', 'region']
        )

        self.action_execution_duration = Histogram(
            'steel_action_execution_duration_seconds',
            'Action execution duration in seconds',
            ['action_type', 'status'],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))
        )

        # System metrics
        self.active_users_gauge = Gauge(
            'steel_active_users',
            'Number of active users in the last 24 hours'
        )

        self.database_connections_gauge = Gauge(
            'steel_database_connections',
            'Number of active database connections'
        )

        self.credential_usage_counter = Counter(
            'steel_credential_usage_total',
            'Total credential usage count',
            ['domain', 'credential_type', 'status']
        )

        # Business metrics
        self.stored_actions_gauge = Gauge(
            'steel_stored_actions_total',
            'Total number of stored actions'
        )

        self.success_rate_gauge = Gauge(
            'steel_action_success_rate',
            'Overall action success rate',
            ['time_window']
        )

        # Performance metrics
        self.steel_session_duration = Histogram(
            'steel_session_duration_seconds',
            'Steel browser session duration in seconds',
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf'))
        )

        self.memory_usage_gauge = Gauge(
            'steel_memory_usage_bytes',
            'Memory usage in bytes'
        )

    def record_action_execution(
        self,
        action_type: str,
        status: str,
        duration: float,
        region: str = "unknown"
    ):
        """Record action execution metrics."""
        self.action_executions_total.labels(
            action_type=action_type,
            status=status,
            region=region
        ).inc()

        self.action_execution_duration.labels(
            action_type=action_type,
            status=status
        ).observe(duration)

    def record_credential_usage(
        self,
        domain: str,
        credential_type: str,
        status: str
    ):
        """Record credential usage metrics."""
        self.credential_usage_counter.labels(
            domain=domain,
            credential_type=credential_type,
            status=status
        ).inc()

    def record_steel_session(self, duration: float):
        """Record Steel session duration."""
        self.steel_session_duration.observe(duration)


class HealthCheckService:
    """Health check and monitoring service."""

    def __init__(self):
        """Initialize health check service."""
        self.metrics = MetricsCollector()
        self._last_metrics_update = 0
        self._metrics_cache = {}
        self._cache_duration = 60  # Cache for 60 seconds

    async def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        start_time = time.time()

        # Basic health checks
        db_healthy = await self._check_database_health()
        redis_healthy = await self._check_redis_health()

        # Performance metrics
        performance_metrics = await self._get_performance_metrics()

        # Determine overall health
        overall_healthy = all([
            db_healthy,
            redis_healthy,
            performance_metrics.get('database_response_time', 0) < 1.0,  # < 1 second
        ])

        health_status = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.version,
            "environment": settings.env,
            "uptime_seconds": time.time() - start_time,
            "checks": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "response_time": performance_metrics.get('database_response_time'),
                },
                "redis": {
                    "status": "healthy" if redis_healthy else "unhealthy",
                },
            },
            "metrics": performance_metrics,
        }

        return health_status

    async def get_readiness_status(self) -> dict[str, Any]:
        """Get readiness status for load balancer."""
        # Check if application is ready to serve requests
        db_ready = await self._check_database_health()

        # Check if critical services are available
        critical_services_ready = await self._check_critical_services()

        is_ready = db_ready and critical_services_ready

        return {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.version,
            "checks": {
                "database": db_ready,
                "critical_services": critical_services_ready,
            }
        }

    async def get_detailed_metrics(self) -> dict[str, Any]:
        """Get detailed application metrics."""
        current_time = time.time()

        # Use cached metrics if recent enough
        if (current_time - self._last_metrics_update) < self._cache_duration and self._metrics_cache:
            return self._metrics_cache

        try:
            async with get_db_session() as db:
                metrics = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "application": await self._get_application_metrics(db),
                    "database": await self._get_database_metrics(db),
                    "business": await self._get_business_metrics(db),
                    "performance": await self._get_performance_metrics(),
                }

                # Update Prometheus gauges
                await self._update_prometheus_metrics(db, metrics)

                # Cache the results
                self._metrics_cache = metrics
                self._last_metrics_update = current_time

                return metrics

        except Exception as e:
            logger.error("Failed to collect detailed metrics", error=str(e))
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Failed to collect metrics",
                "status": "degraded"
            }

    async def _check_database_health(self) -> bool:
        """Check database connectivity and basic operations."""
        try:
            async with get_db_session() as db:
                start_time = time.time()
                result = await db.execute(text("SELECT 1"))
                response_time = time.time() - start_time

                # Check if response time is reasonable
                if response_time > 5.0:  # 5 seconds
                    logger.warning("Database response time is high", response_time=response_time)
                    return False

                return result.scalar() == 1

        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

    async def _check_redis_health(self) -> bool:
        """Check Redis connectivity."""
        try:
            # TODO: Implement Redis health check when Redis is integrated
            # For now, assume Redis is healthy if it's configured
            return bool(settings.redis_url)
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False

    async def _check_critical_services(self) -> bool:
        """Check if critical services are available."""
        try:
            # Check if we can create a database session
            async with get_db_session():
                pass

            # Check if configuration is valid
            settings.validate_required_keys()

            return True

        except Exception as e:
            logger.error("Critical services check failed", error=str(e))
            return False

    async def _get_application_metrics(self, db: AsyncSession) -> dict[str, Any]:
        """Get application-level metrics."""
        try:
            # Count total users
            user_count_result = await db.execute(select(func.count(User.id)))
            total_users = user_count_result.scalar() or 0

            # Count active users (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            active_users_result = await db.execute(
                select(func.count(User.id)).where(User.last_login >= yesterday)
            )
            active_users = active_users_result.scalar() or 0

            # Count total executions
            execution_count_result = await db.execute(select(func.count(ExecutionRun.id)))
            total_executions = execution_count_result.scalar() or 0

            return {
                "total_users": total_users,
                "active_users_24h": active_users,
                "total_executions": total_executions,
                "version": settings.version,
                "environment": settings.env,
            }

        except Exception as e:
            logger.error("Failed to get application metrics", error=str(e))
            return {"error": "Failed to collect application metrics"}

    async def _get_database_metrics(self, db: AsyncSession) -> dict[str, Any]:
        """Get database performance metrics."""
        try:
            start_time = time.time()

            # Test query performance
            await db.execute(text("SELECT 1"))
            query_time = time.time() - start_time

            # Get connection pool info (simplified)
            return {
                "connection_pool_size": 10,  # TODO: Get actual pool size
                "active_connections": 1,     # TODO: Get actual connection count
                "query_response_time": query_time,
                "status": "healthy" if query_time < 1.0 else "slow",
            }

        except Exception as e:
            logger.error("Failed to get database metrics", error=str(e))
            return {"error": "Failed to collect database metrics"}

    async def _get_business_metrics(self, db: AsyncSession) -> dict[str, Any]:
        """Get business-specific metrics."""
        try:
            # Count stored actions
            stored_actions_result = await db.execute(select(func.count(StoredAction.id)))
            total_stored_actions = stored_actions_result.scalar() or 0

            # Count executions by status in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)

            success_count_result = await db.execute(
                select(func.count(ExecutionRun.id)).where(
                    ExecutionRun.created_at >= yesterday,
                    ExecutionRun.status == 'completed'
                )
            )
            success_count = success_count_result.scalar() or 0

            total_recent_result = await db.execute(
                select(func.count(ExecutionRun.id)).where(ExecutionRun.created_at >= yesterday)
            )
            total_recent = total_recent_result.scalar() or 0

            success_rate = (success_count / total_recent * 100) if total_recent > 0 else 0

            return {
                "total_stored_actions": total_stored_actions,
                "executions_last_24h": total_recent,
                "success_rate_24h": round(success_rate, 2),
                "failed_executions_24h": total_recent - success_count,
            }

        except Exception as e:
            logger.error("Failed to get business metrics", error=str(e))
            return {"error": "Failed to collect business metrics"}

    async def _get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        try:
            start_time = time.time()

            # Test database response time
            async with get_db_session() as db:
                db_start = time.time()
                await db.execute(text("SELECT 1"))
                db_response_time = time.time() - db_start

            total_time = time.time() - start_time

            return {
                "database_response_time": round(db_response_time, 3),
                "total_health_check_time": round(total_time, 3),
                "memory_usage_mb": 0,  # TODO: Implement memory usage tracking
                "cpu_usage_percent": 0,  # TODO: Implement CPU usage tracking
            }

        except Exception as e:
            logger.error("Failed to get performance metrics", error=str(e))
            return {
                "database_response_time": None,
                "total_health_check_time": None,
                "error": "Failed to collect performance metrics"
            }

    async def _update_prometheus_metrics(self, db: AsyncSession, metrics: dict[str, Any]) -> None:
        """Update Prometheus gauges with collected metrics."""
        try:
            app_metrics = metrics.get("application", {})
            business_metrics = metrics.get("business", {})

            # Update gauges
            if "active_users_24h" in app_metrics:
                self.metrics.active_users_gauge.set(app_metrics["active_users_24h"])

            if "total_stored_actions" in business_metrics:
                self.metrics.stored_actions_gauge.set(business_metrics["total_stored_actions"])

            if "success_rate_24h" in business_metrics:
                self.metrics.success_rate_gauge.labels(time_window="24h").set(
                    business_metrics["success_rate_24h"] / 100
                )

        except Exception as e:
            logger.warning("Failed to update Prometheus metrics", error=str(e))


# Global monitoring service instance
monitoring_service = HealthCheckService()
