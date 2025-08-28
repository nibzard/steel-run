"""Tests for monitoring API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.user import User


class TestHealthEndpoints:
    """Test health check and readiness endpoints."""
    
    async def test_health_check(self, async_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await async_client.get("/api/v1/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data
    
    async def test_health_check_detailed(self, async_client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await async_client.get("/api/v1/health/detailed")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "steel_api" in data
        assert "redis" in data
        assert "services" in data
        
        # Check individual service status
        assert data["database"]["status"] in ["healthy", "unhealthy"]
        assert data["steel_api"]["status"] in ["healthy", "unhealthy"]
        assert data["redis"]["status"] in ["healthy", "unhealthy"]
    
    async def test_readiness_check(self, async_client: AsyncClient):
        """Test Kubernetes readiness probe endpoint."""
        response = await async_client.get("/api/v1/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ready"] is True
        assert "checks" in data
    
    async def test_liveness_check(self, async_client: AsyncClient):
        """Test Kubernetes liveness probe endpoint."""
        response = await async_client.get("/api/v1/live")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["alive"] is True


class TestMetricsEndpoints:
    """Test Prometheus metrics endpoints."""
    
    async def test_prometheus_metrics(self, async_client: AsyncClient):
        """Test Prometheus metrics endpoint."""
        response = await async_client.get("/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        content = response.text
        
        # Check for expected metric families
        assert "steel_actions_total" in content
        assert "steel_action_duration_seconds" in content
        assert "steel_api_requests_total" in content
        assert "steel_api_request_duration_seconds" in content
        assert "steel_sessions_active" in content
        assert "steel_credentials_total" in content
    
    async def test_metrics_authentication_not_required(self, async_client: AsyncClient):
        """Test that metrics endpoint doesn't require authentication."""
        # Should work without auth headers
        response = await async_client.get("/metrics")
        assert response.status_code == status.HTTP_200_OK
    
    async def test_custom_metrics_format(self, async_client: AsyncClient):
        """Test custom metrics format and labels."""
        response = await async_client.get("/metrics")
        content = response.text
        
        # Check for expected labels and format
        metric_lines = [line for line in content.split('\n') if line and not line.startswith('#')]
        
        for line in metric_lines:
            # Basic metric format validation
            if '{' in line:
                assert '}' in line
                assert line.count('{') == line.count('}')


class TestSystemStatusAPI:
    """Test system status and information endpoints."""
    
    async def test_system_info(self, async_client: AsyncClient, auth_headers: dict):
        """Test system information endpoint."""
        response = await async_client.get(
            "/api/v1/system/info", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data
        assert "deployment_time" in data
        assert "commit_hash" in data
    
    async def test_system_stats(self, async_client: AsyncClient, auth_headers: dict):
        """Test system statistics endpoint."""
        response = await async_client.get(
            "/api/v1/system/stats", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_users" in data
        assert "total_actions" in data
        assert "total_executions" in data
        assert "active_sessions" in data
        assert "uptime_seconds" in data
        
        # Verify data types
        assert isinstance(data["total_users"], int)
        assert isinstance(data["total_actions"], int)
        assert isinstance(data["total_executions"], int)
        assert isinstance(data["uptime_seconds"], (int, float))
    
    async def test_system_stats_unauthorized(self, async_client: AsyncClient):
        """Test that system stats require authentication."""
        response = await async_client.get("/api/v1/system/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_database_status(self, async_client: AsyncClient, auth_headers: dict):
        """Test database status endpoint."""
        response = await async_client.get(
            "/api/v1/system/database", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "connection_pool" in data
        assert "migrations" in data
        
        # Connection pool info
        pool_info = data["connection_pool"]
        assert "active_connections" in pool_info
        assert "total_connections" in pool_info
        assert "max_connections" in pool_info


class TestPerformanceMonitoring:
    """Test performance monitoring endpoints."""
    
    async def test_performance_metrics(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test performance metrics endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/performance", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "response_times" in data
        assert "throughput" in data
        assert "error_rates" in data
        assert "resource_usage" in data
        
        # Response times
        response_times = data["response_times"]
        assert "p50" in response_times
        assert "p95" in response_times
        assert "p99" in response_times
        assert "average" in response_times
        
        # Throughput
        throughput = data["throughput"]
        assert "requests_per_second" in throughput
        assert "actions_per_minute" in throughput
        
        # Error rates
        error_rates = data["error_rates"]
        assert "http_errors" in error_rates
        assert "action_failures" in error_rates
        assert "api_errors" in error_rates
    
    async def test_action_performance_stats(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test action-specific performance statistics."""
        response = await async_client.get(
            "/api/v1/monitoring/actions/performance", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are any actions
            action_stat = data[0]
            assert "action_type" in action_stat
            assert "total_executions" in action_stat
            assert "success_rate" in action_stat
            assert "avg_execution_time" in action_stat
            assert "p95_execution_time" in action_stat
    
    async def test_user_performance_stats(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test user-specific performance statistics."""
        response = await async_client.get(
            "/api/v1/monitoring/users/performance", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_actions" in data
        assert "success_rate" in data
        assert "avg_response_time" in data
        assert "last_24h_activity" in data


class TestErrorMonitoring:
    """Test error monitoring and reporting endpoints."""
    
    async def test_error_summary(self, async_client: AsyncClient, auth_headers: dict):
        """Test error summary endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/errors/summary", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_errors" in data
        assert "error_rate" in data
        assert "top_errors" in data
        assert "errors_by_type" in data
        
        # Top errors should be a list
        assert isinstance(data["top_errors"], list)
        
        # Errors by type should be a dict
        assert isinstance(data["errors_by_type"], dict)
    
    async def test_error_details(self, async_client: AsyncClient, auth_headers: dict):
        """Test detailed error information endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/errors?limit=10", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "errors" in data
        assert "total" in data
        assert "page" in data
        
        errors = data["errors"]
        assert isinstance(errors, list)
        
        if errors:  # If there are errors
            error = errors[0]
            assert "id" in error
            assert "timestamp" in error
            assert "error_type" in error
            assert "message" in error
            assert "context" in error
    
    async def test_action_errors(self, async_client: AsyncClient, auth_headers: dict):
        """Test action-specific error monitoring."""
        response = await async_client.get(
            "/api/v1/monitoring/actions/errors", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are action errors
            action_error = data[0]
            assert "action_type" in action_error
            assert "error_count" in action_error
            assert "error_rate" in action_error
            assert "recent_errors" in action_error


class TestAlertingEndpoints:
    """Test alerting and notification endpoints."""
    
    async def test_active_alerts(self, async_client: AsyncClient, auth_headers: dict):
        """Test active alerts endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/alerts", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        
        alerts = data["alerts"]
        assert isinstance(alerts, list)
        
        if alerts:  # If there are active alerts
            alert = alerts[0]
            assert "id" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "timestamp" in alert
            assert "status" in alert
    
    async def test_alert_configuration(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test alert configuration endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/alerts/config", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "rules" in data
        assert "channels" in data
        
        # Alert rules
        rules = data["rules"]
        assert isinstance(rules, list)
        
        if rules:
            rule = rules[0]
            assert "name" in rule
            assert "condition" in rule
            assert "threshold" in rule
            assert "enabled" in rule
    
    async def test_update_alert_config(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test updating alert configuration."""
        config_update = {
            "rules": [
                {
                    "name": "High Error Rate",
                    "condition": "error_rate > 0.05",
                    "threshold": 0.05,
                    "enabled": True,
                    "severity": "warning"
                }
            ]
        }
        
        response = await async_client.put(
            "/api/v1/monitoring/alerts/config",
            json=config_update,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Alert configuration updated successfully"


class TestLogEndpoints:
    """Test log access and search endpoints."""
    
    async def test_recent_logs(self, async_client: AsyncClient, auth_headers: dict):
        """Test recent logs endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/logs?limit=50", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "logs" in data
        assert "total" in data
        
        logs = data["logs"]
        assert isinstance(logs, list)
        assert len(logs) <= 50
        
        if logs:
            log_entry = logs[0]
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry
            assert "logger" in log_entry
    
    async def test_log_search(self, async_client: AsyncClient, auth_headers: dict):
        """Test log search functionality."""
        search_params = {
            "query": "error",
            "level": "ERROR",
            "limit": 20,
            "start_time": "2024-01-01T00:00:00Z",
        }
        
        response = await async_client.get(
            "/api/v1/monitoring/logs/search",
            params=search_params,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert "query" in data
        
        # Should only return error level logs
        logs = data["logs"]
        if logs:
            for log_entry in logs:
                assert log_entry["level"] == "ERROR"
    
    async def test_action_logs(self, async_client: AsyncClient, auth_headers: dict):
        """Test action-specific log retrieval."""
        # This would typically require an execution ID
        execution_id = "test-execution-id"
        
        response = await async_client.get(
            f"/api/v1/monitoring/actions/{execution_id}/logs",
            headers=auth_headers,
        )
        
        # Might return 404 if execution doesn't exist, which is fine for tests
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "logs" in data
            assert "execution_id" in data


class TestSecurityMonitoring:
    """Test security monitoring endpoints."""
    
    async def test_security_events(self, async_client: AsyncClient, auth_headers: dict):
        """Test security events endpoint."""
        response = await async_client.get(
            "/api/v1/monitoring/security/events", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "events" in data
        assert "total" in data
        
        events = data["events"]
        assert isinstance(events, list)
        
        if events:
            event = events[0]
            assert "id" in event
            assert "timestamp" in event
            assert "event_type" in event
            assert "severity" in event
            assert "description" in event
    
    async def test_rate_limit_status(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test rate limit monitoring."""
        response = await async_client.get(
            "/api/v1/monitoring/security/rate-limits", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "limits" in data
        
        limits = data["limits"]
        assert isinstance(limits, list)
        
        if limits:
            limit_info = limits[0]
            assert "key" in limit_info
            assert "current_usage" in limit_info
            assert "limit" in limit_info
            assert "reset_time" in limit_info
    
    async def test_suspicious_activity(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test suspicious activity monitoring."""
        response = await async_client.get(
            "/api/v1/monitoring/security/suspicious", headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "activities" in data
        assert "summary" in data
        
        summary = data["summary"]
        assert "total_suspicious_events" in summary
        assert "high_risk_events" in summary
        assert "blocked_requests" in summary


@pytest.mark.performance
class TestMonitoringPerformance:
    """Test monitoring endpoint performance."""
    
    async def test_metrics_endpoint_performance(self, async_client: AsyncClient):
        """Test that metrics endpoint responds quickly."""
        import time
        
        start_time = time.time()
        response = await async_client.get("/metrics")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        # Metrics endpoint should respond within 1 second
        assert (end_time - start_time) < 1.0
    
    async def test_health_check_performance(self, async_client: AsyncClient):
        """Test that health check responds quickly."""
        import time
        
        start_time = time.time()
        response = await async_client.get("/api/v1/health")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        # Health check should respond within 0.5 seconds
        assert (end_time - start_time) < 0.5


@pytest.mark.security
class TestMonitoringSecurity:
    """Test security aspects of monitoring endpoints."""
    
    async def test_sensitive_data_not_exposed(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test that monitoring endpoints don't expose sensitive data."""
        endpoints = [
            "/api/v1/system/info",
            "/api/v1/system/stats",
            "/api/v1/monitoring/performance",
            "/api/v1/monitoring/errors/summary",
        ]
        
        sensitive_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "private",
        ]
        
        for endpoint in endpoints:
            response = await async_client.get(endpoint, headers=auth_headers)
            if response.status_code == status.HTTP_200_OK:
                content = response.text.lower()
                for pattern in sensitive_patterns:
                    # Some patterns might be acceptable in field names
                    # but not in values
                    if pattern in content:
                        # Ensure it's not exposing actual sensitive values
                        assert f'"{pattern}": "' not in content or \
                               f'"{pattern}": "***' in content or \
                               f'"{pattern}": "[REDACTED]"' in content
    
    async def test_monitoring_requires_authentication(self, async_client: AsyncClient):
        """Test that sensitive monitoring endpoints require authentication."""
        protected_endpoints = [
            "/api/v1/system/info",
            "/api/v1/system/stats",
            "/api/v1/monitoring/performance",
            "/api/v1/monitoring/errors/summary",
            "/api/v1/monitoring/alerts",
        ]
        
        for endpoint in protected_endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED