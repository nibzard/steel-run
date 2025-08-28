"""Rate limiting middleware for API endpoints."""

import time

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using in-memory storage.

    In production, this should be replaced with Redis-based rate limiting
    for distributed deployments.
    """

    def __init__(self, app):
        super().__init__(app)
        # In-memory rate limit storage
        # Format: {key: {'count': int, 'window_start': float, 'limit': int, 'window': int}}
        self.rate_limits: dict[str, dict] = {}
        self.cleanup_interval = 300  # Clean up old entries every 5 minutes
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting if disabled
        if not settings.enable_rate_limiting:
            return await call_next(request)

        # Skip rate limiting for certain paths
        if self._should_skip_rate_limiting(request.url.path):
            return await call_next(request)

        # Determine rate limit key and settings
        rate_limit_key, limit, window = await self._get_rate_limit_settings(request)

        if rate_limit_key:
            # Check and update rate limit
            if not await self._check_rate_limit(rate_limit_key, limit, window):
                # Get remaining time
                remaining_time = await self._get_reset_time(rate_limit_key, window)

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time() + remaining_time)),
                        "Retry-After": str(int(remaining_time)),
                    },
                )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if rate_limit_key:
            remaining = await self._get_remaining_requests(rate_limit_key, limit, window)
            reset_time = await self._get_reset_time(rate_limit_key, window)

            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + reset_time))

        return response

    def _should_skip_rate_limiting(self, path: str) -> bool:
        """Check if rate limiting should be skipped for this path."""
        skip_paths = [
            "/health",
            "/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static/",
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    async def _get_rate_limit_settings(self, request: Request) -> tuple[str | None, int, int]:
        """
        Get rate limit settings for the request.

        Returns:
            Tuple of (rate_limit_key, limit, window_seconds)
        """
        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if user is authenticated (API key or JWT)
        user_key = await self._get_user_key(request)

        if user_key:
            # Authenticated user rate limit
            return f"user:{user_key}", settings.rate_limit_per_user, 3600  # 1 hour window
        else:
            # IP-based rate limit
            return f"ip:{client_ip}", settings.rate_limit_per_ip, 3600  # 1 hour window

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to client host
        return request.client.host if request.client else "unknown"

    async def _get_user_key(self, request: Request) -> str | None:
        """
        Get user identifier from authentication headers.

        Returns:
            User identifier if authenticated, None otherwise
        """
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key[:12]}"  # Use key prefix as identifier

        # Check for JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from ..utils.auth import verify_token
                payload = verify_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"jwt:{user_id}"
            except Exception:
                # Invalid token, treat as unauthenticated
                pass

        return None

    async def _check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key
            limit: Request limit
            window: Time window in seconds

        Returns:
            True if within limit, False otherwise
        """
        current_time = time.time()

        # Clean up old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_entries()
            self.last_cleanup = current_time

        # Get or create rate limit entry
        if key not in self.rate_limits:
            self.rate_limits[key] = {
                'count': 0,
                'window_start': current_time,
                'limit': limit,
                'window': window,
            }

        rate_limit = self.rate_limits[key]

        # Check if we're in a new window
        if current_time - rate_limit['window_start'] >= window:
            # Reset for new window
            rate_limit['count'] = 0
            rate_limit['window_start'] = current_time

        # Check if within limit
        if rate_limit['count'] >= limit:
            return False

        # Increment counter
        rate_limit['count'] += 1

        return True

    async def _get_remaining_requests(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests in current window."""
        if key not in self.rate_limits:
            return limit

        rate_limit = self.rate_limits[key]
        current_time = time.time()

        # Check if we're in a new window
        if current_time - rate_limit['window_start'] >= window:
            return limit

        return max(0, limit - rate_limit['count'])

    async def _get_reset_time(self, key: str, window: int) -> float:
        """Get time until rate limit resets."""
        if key not in self.rate_limits:
            return 0

        rate_limit = self.rate_limits[key]
        current_time = time.time()

        return max(0, window - (current_time - rate_limit['window_start']))

    async def _cleanup_old_entries(self):
        """Clean up old rate limit entries."""
        current_time = time.time()
        keys_to_remove = []

        for key, rate_limit in self.rate_limits.items():
            # Remove entries older than 2 hours
            if current_time - rate_limit['window_start'] > 7200:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.rate_limits[key]


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to whitelist specific IP addresses.

    Useful for allowing unlimited access from internal services.
    """

    def __init__(self, app, whitelisted_ips: list | None = None):
        super().__init__(app)
        self.whitelisted_ips = set(whitelisted_ips or [])
        # Add common internal IPs
        self.whitelisted_ips.update([
            "127.0.0.1",
            "localhost",
            "::1",
        ])

    async def dispatch(self, request: Request, call_next):
        """Process request with IP whitelisting."""
        client_ip = self._get_client_ip(request)

        if client_ip in self.whitelisted_ips:
            # Add header to indicate whitelisted IP
            response = await call_next(request)
            response.headers["X-IP-Whitelisted"] = "true"
            return response

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to client host
        return request.client.host if request.client else "unknown"
