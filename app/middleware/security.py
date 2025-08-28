"""Security middleware for Steel.run platform."""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from ..core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add comprehensive security headers."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers to all responses."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"  
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.steel.dev wss: ws:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # HSTS for HTTPS (only in production)
        if settings.env == "production" or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Feature Policy (Permissions Policy)
        feature_policy = (
            "camera 'none'; "
            "microphone 'none'; "
            "geolocation 'none'; "
            "payment 'none'; "
            "usb 'none'"
        )
        response.headers["Permissions-Policy"] = feature_policy
        
        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Server header (obscure server info)
        response.headers["Server"] = "Steel.run"
        
        # Cache control for sensitive endpoints
        if any(path in str(request.url) for path in ["/api/", "/auth/", "/credentials/"]):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for security-focused request logging."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log requests for security monitoring."""
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log security-relevant requests
        if self._is_security_relevant(request, response):
            import structlog
            logger = structlog.get_logger(__name__)
            
            logger.info(
                "Security event",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                client_ip=client_ip,
                user_agent=user_agent,
                process_time=process_time,
                content_length=response.headers.get("content-length", 0)
            )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    def _is_security_relevant(self, request: Request, response: Response) -> bool:
        """Check if request is security-relevant for logging."""
        # Log all auth endpoints
        if "/auth/" in str(request.url):
            return True
        
        # Log failed requests
        if response.status_code >= 400:
            return True
        
        # Log credential operations
        if "/credentials/" in str(request.url):
            return True
        
        # Log API key operations
        if "/api-keys/" in str(request.url):
            return True
        
        # Log admin operations
        if "/admin/" in str(request.url):
            return True
        
        return False


class RateLimitSecurityMiddleware(BaseHTTPMiddleware):
    """Additional rate limiting for security-sensitive endpoints."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_counts = {}  # Simple in-memory store
        self.last_reset = time.time()
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply enhanced rate limiting for sensitive endpoints."""
        # Reset counts every hour
        current_time = time.time()
        if current_time - self.last_reset > 3600:
            self.request_counts.clear()
            self.last_reset = current_time
        
        client_ip = request.client.host if request.client else "unknown"
        endpoint_key = f"{client_ip}:{request.url.path}"
        
        # Apply stricter limits for sensitive endpoints
        if self._is_sensitive_endpoint(request):
            limit = 10  # 10 requests per hour for sensitive endpoints
            current_count = self.request_counts.get(endpoint_key, 0)
            
            if current_count >= limit:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded for sensitive endpoint"
                )
            
            self.request_counts[endpoint_key] = current_count + 1
        
        return await call_next(request)
    
    def _is_sensitive_endpoint(self, request: Request) -> bool:
        """Check if endpoint is security-sensitive."""
        sensitive_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register", 
            "/api/v1/auth/reset-password",
            "/api/v1/credentials",
            "/api/v1/api-keys"
        ]
        
        return any(path in str(request.url) for path in sensitive_paths)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware for input sanitization and validation."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint  
    ) -> Response:
        """Sanitize and validate inputs."""
        # Check for potentially malicious patterns in URL
        url_str = str(request.url)
        
        # Block common attack patterns
        suspicious_patterns = [
            "../",  # Path traversal
            "<script",  # XSS
            "javascript:",  # JavaScript injection
            "data:text/html",  # Data URL XSS
            "vbscript:",  # VBScript injection
            "onload=",  # Event handler injection
            "onerror=",  # Event handler injection
            "\\x",  # Hex encoding
            "%3c",  # URL encoded <
            "%3e",  # URL encoded >
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in url_str.lower():
                from fastapi import HTTPException
                import structlog
                
                logger = structlog.get_logger(__name__)
                logger.warning(
                    "Suspicious request blocked",
                    url=url_str,
                    pattern=pattern,
                    client_ip=request.client.host if request.client else "unknown"
                )
                
                raise HTTPException(
                    status_code=400,
                    detail="Request contains suspicious patterns"
                )
        
        return await call_next(request)


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security considerations."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle CORS with security checks."""
        response = await call_next(request)
        
        # Get origin
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        allowed_origins = settings.cors_origins
        
        if origin and self._is_origin_allowed(origin, allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Accept, Accept-Language, Content-Language, Content-Type, "
                "Authorization, X-API-Key, X-Requested-With"
            )
            response.headers["Access-Control-Max-Age"] = "86400"
        else:
            # No CORS headers for disallowed origins
            pass
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response.status_code = 204
        
        return response
    
    def _is_origin_allowed(self, origin: str, allowed_origins: list[str]) -> bool:
        """Check if origin is in allowed list."""
        # Exact match
        if origin in allowed_origins:
            return True
        
        # Wildcard match for development
        if settings.env == "development" and "*" in allowed_origins:
            return True
        
        # Pattern matching for subdomains (be careful with this)
        for allowed in allowed_origins:
            if allowed.startswith("*.") and origin.endswith(allowed[1:]):
                return True
        
        return False