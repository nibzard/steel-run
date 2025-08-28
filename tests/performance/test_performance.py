"""Performance tests using pytest for Steel.run platform."""

import asyncio
import time
import pytest
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.performance
class TestAPIPerformance:
    """Test API endpoint performance."""

    @pytest.mark.asyncio
    async def test_health_endpoint_response_time(self):
        """Test health endpoint responds quickly."""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get("http://localhost:8000/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_time = end_time - start_time
            assert response_time < 1.0  # Should respond in less than 1 second

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test system handles concurrent health checks."""
        async with httpx.AsyncClient() as client:
            # Create 50 concurrent requests
            tasks = []
            for _ in range(50):
                task = client.get("http://localhost:8000/health")
                tasks.append(task)
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
            
            # Should handle 50 concurrent requests in reasonable time
            total_time = end_time - start_time
            assert total_time < 5.0  # Less than 5 seconds for 50 requests

    @pytest.mark.asyncio
    async def test_actions_list_performance(self):
        """Test actions listing performance."""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get("http://localhost:8000/api/v1/actions")
            end_time = time.time()
            
            # May return 401 without auth, but should be fast
            assert response.status_code in [200, 401]
            response_time = end_time - start_time
            assert response_time < 2.0

    @pytest.mark.asyncio
    async def test_metrics_endpoint_performance(self):
        """Test metrics endpoint performance."""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get("http://localhost:8000/metrics")
            end_time = time.time()
            
            assert response.status_code == 200
            response_time = end_time - start_time
            assert response_time < 2.0  # Metrics collection should be fast

    def test_database_connection_pool_stress(self):
        """Test database connection pool under stress."""
        def make_request():
            import requests
            try:
                response = requests.get("http://localhost:8000/health/db", timeout=10)
                return response.status_code
            except Exception as e:
                return 500

        # Create thread pool for concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit 100 requests
            futures = [executor.submit(make_request) for _ in range(100)]
            
            results = []
            for future in as_completed(futures, timeout=30):
                try:
                    status_code = future.result()
                    results.append(status_code)
                except Exception as e:
                    results.append(500)
        
        # Most requests should succeed
        success_rate = sum(1 for code in results if code == 200) / len(results)
        assert success_rate > 0.8  # At least 80% success rate


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage and leaks."""

    @pytest.mark.asyncio
    async def test_memory_stability_under_load(self):
        """Test memory doesn't grow excessively under load."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        async with httpx.AsyncClient() as client:
            for i in range(100):
                await client.get("http://localhost:8000/health")
                
                # Check memory every 20 requests
                if i % 20 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_growth = current_memory - initial_memory
                    
                    # Memory growth should be reasonable (less than 50MB)
                    assert memory_growth < 50, f"Memory grew by {memory_growth}MB after {i} requests"


@pytest.mark.performance
class TestScalability:
    """Test system scalability characteristics."""

    @pytest.mark.asyncio
    async def test_response_time_scalability(self):
        """Test response times remain reasonable as load increases."""
        async with httpx.AsyncClient() as client:
            # Test different load levels
            for concurrent_requests in [1, 5, 10, 20]:
                response_times = []
                
                # Create tasks
                tasks = []
                for _ in range(concurrent_requests):
                    task = self._timed_request(client, "http://localhost:8000/health")
                    tasks.append(task)
                
                # Execute and collect times
                results = await asyncio.gather(*tasks)
                response_times.extend(results)
                
                # Calculate average response time
                avg_response_time = sum(response_times) / len(response_times)
                
                # Response time should stay reasonable even with more concurrent requests
                if concurrent_requests <= 10:
                    assert avg_response_time < 1.0
                else:
                    assert avg_response_time < 3.0  # Allow higher times for stress conditions

    async def _timed_request(self, client, url):
        """Make a timed request and return response time."""
        start_time = time.time()
        response = await client.get(url)
        end_time = time.time()
        
        assert response.status_code == 200
        return end_time - start_time

    @pytest.mark.asyncio
    async def test_throughput_capacity(self):
        """Test system throughput capacity."""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            # Make 200 requests as fast as possible
            tasks = []
            for _ in range(200):
                task = client.get("http://localhost:8000/health")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
            
            # Calculate throughput
            total_time = end_time - start_time
            throughput = 200 / total_time  # requests per second
            
            # Should handle at least 20 requests per second
            assert throughput > 20, f"Throughput was {throughput:.2f} req/s, expected > 20"


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database operation performance."""

    def test_health_check_db_performance(self):
        """Test database health check performance."""
        import requests
        
        # Make multiple database health checks
        response_times = []
        for _ in range(20):
            start_time = time.time()
            response = requests.get("http://localhost:8000/health/db")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Average response time should be reasonable
        avg_time = sum(response_times) / len(response_times)
        assert avg_time < 1.0  # Less than 1 second on average
        
        # No single request should take too long
        max_time = max(response_times)
        assert max_time < 3.0  # No request should take more than 3 seconds


@pytest.mark.performance
@pytest.mark.slow
class TestLongRunningPerformance:
    """Test performance over longer periods."""

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self):
        """Test performance under sustained load."""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            total_requests = 0
            failures = 0
            
            # Run for 30 seconds with constant load
            while time.time() - start_time < 30:
                try:
                    response = await client.get("http://localhost:8000/health")
                    if response.status_code != 200:
                        failures += 1
                    total_requests += 1
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.1)
                    
                except Exception:
                    failures += 1
                    total_requests += 1
            
            # Calculate success rate and throughput
            success_rate = (total_requests - failures) / total_requests
            throughput = total_requests / 30  # requests per second
            
            # Should maintain high success rate and reasonable throughput
            assert success_rate > 0.95  # 95% success rate
            assert throughput > 5  # At least 5 requests per second
            assert total_requests > 100  # Should handle substantial load


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance"])