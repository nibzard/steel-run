"""Locust performance testing configuration for Steel.run."""

import json
import random
import time
from locust import HttpUser, task, between


class SteelRunUser(HttpUser):
    """Simulate Steel.run platform user behavior."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Setup user session."""
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Steel.run Load Test"
        }
        
        # Try to authenticate (will fail but that's expected in load test)
        self.client.post(
            "/api/v1/auth/login",
            json={
                "email": f"loadtest{random.randint(1, 1000)}@example.com",
                "password": "testpassword123"
            },
            headers=self.headers,
            catch_response=True
        )

    @task(10)
    def health_check(self):
        """Test health endpoint - most frequent."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")

    @task(8)
    def list_actions(self):
        """Test listing available actions."""
        with self.client.get("/api/v1/actions", headers=self.headers, catch_response=True) as response:
            if response.status_code not in [200, 401]:  # 401 expected without auth
                response.failure(f"List actions failed: {response.status_code}")

    @task(5)
    def get_stored_actions(self):
        """Test getting stored actions (will require auth)."""
        with self.client.get("/api/v1/stored-actions", headers=self.headers, catch_response=True) as response:
            if response.status_code not in [200, 401, 403]:
                response.failure(f"Get stored actions failed: {response.status_code}")

    @task(3)
    def create_stored_action(self):
        """Test creating a stored action (will require auth)."""
        action_data = {
            "name": f"Load Test Action {random.randint(1, 10000)}",
            "description": "Performance test action",
            "action_type": "website",
            "parameters": {
                "url": "https://example.com",
                "action": "screenshot"
            }
        }
        
        with self.client.post(
            "/api/v1/stored-actions",
            json=action_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code not in [201, 401, 403]:
                response.failure(f"Create stored action failed: {response.status_code}")

    @task(2)
    def execute_action(self):
        """Test action execution (will require auth)."""
        execution_data = {
            "parameters": {
                "url": "https://httpbin.org/status/200"
            }
        }
        
        with self.client.post(
            f"/api/v1/actions/website-screenshot/execute",
            json=execution_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code not in [200, 202, 401, 403]:
                response.failure(f"Execute action failed: {response.status_code}")

    @task(1)
    def get_metrics(self):
        """Test metrics endpoint."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Metrics failed: {response.status_code}")

    @task(1)
    def websocket_connection(self):
        """Simulate WebSocket connection attempt."""
        # This is a simplified WebSocket test - in practice you'd use websocket-client
        # For load testing WebSockets, consider using specialized tools
        pass


class AdminUser(HttpUser):
    """Simulate admin user behavior with higher privileges."""
    
    wait_time = between(2, 5)
    weight = 1  # Less frequent than regular users
    
    def on_start(self):
        """Setup admin session."""
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Steel.run Admin Load Test"
        }

    @task(5)
    def monitoring_stats(self):
        """Test monitoring endpoints."""
        with self.client.get("/api/v1/monitoring/stats", headers=self.headers, catch_response=True) as response:
            if response.status_code not in [200, 401, 403]:
                response.failure(f"Monitoring stats failed: {response.status_code}")

    @task(3)
    def system_health(self):
        """Test system health checks."""
        endpoints = ["/health", "/health/db", "/health/dependencies"]
        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code != 200:
                    response.failure(f"Health check {endpoint} failed: {response.status_code}")

    @task(2)
    def bulk_operations(self):
        """Test bulk operations."""
        bulk_data = {
            "action_ids": [f"action_{i}" for i in range(5)],
            "operation": "enable"
        }
        
        with self.client.post(
            "/api/v1/bulk-operations/stored-actions",
            json=bulk_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code not in [200, 401, 403]:
                response.failure(f"Bulk operations failed: {response.status_code}")


class DatabaseStressUser(HttpUser):
    """Simulate database-intensive operations."""
    
    wait_time = between(0.5, 2)
    weight = 2  # More frequent to stress database
    
    def on_start(self):
        """Setup database stress session."""
        self.headers = {"Content-Type": "application/json"}

    @task(10)
    def rapid_health_checks(self):
        """Rapid health checks to stress database connections."""
        with self.client.get("/health/db", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"DB health check failed: {response.status_code}")

    @task(5)
    def concurrent_queries(self):
        """Multiple concurrent API calls to stress connection pool."""
        # List actions
        self.client.get("/api/v1/actions", headers=self.headers, catch_response=True)
        
        # Get stored actions
        self.client.get("/api/v1/stored-actions", headers=self.headers, catch_response=True)
        
        # Get credentials  
        self.client.get("/api/v1/credentials", headers=self.headers, catch_response=True)


# Performance test scenarios
class SpikeTesting(HttpUser):
    """Simulate traffic spikes."""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    weight = 1
    
    @task
    def spike_requests(self):
        """Generate rapid requests to test spike handling."""
        endpoints = [
            "/health",
            "/api/v1/actions", 
            "/metrics"
        ]
        
        endpoint = random.choice(endpoints)
        with self.client.get(endpoint, catch_response=True) as response:
            if response.status_code not in [200, 401]:
                response.failure(f"Spike test failed on {endpoint}: {response.status_code}")
                
                
# Test configuration
if __name__ == "__main__":
    # This allows running locust with custom scenarios
    print("Steel.run Load Testing Configuration")
    print("Available user types:")
    print("- SteelRunUser: Normal user behavior")
    print("- AdminUser: Admin operations") 
    print("- DatabaseStressUser: Database stress testing")
    print("- SpikeTesting: Traffic spike simulation")
    print()
    print("Run with: locust -f locustfile.py --host=http://localhost:8000")