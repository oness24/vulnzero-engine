"""Middleware for VulnZero API Gateway."""
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from vulnzero.shared.config import get_settings

settings = get_settings()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    API Key authentication middleware.

    Validates API key from Authorization header or X-API-Key header.
    """

    # Public endpoints that don't require authentication
    PUBLIC_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/database",
        "/api/v1/health/ready",
        "/api/v1/health/live",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and validate authentication.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from next handler or error response
        """
        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip authentication in development mode if configured
        if settings.environment == "development" and not settings.require_auth_in_dev:
            return await call_next(request)

        # Get API key from headers
        api_key = self._extract_api_key(request)

        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Missing API key. Provide via Authorization header or X-API-Key header."
                },
            )

        # Validate API key
        if not self._validate_api_key(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )

        # Add user info to request state for downstream use
        request.state.api_key = api_key
        request.state.authenticated = True

        # Continue to next middleware/handler
        response = await call_next(request)
        return response

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers.

        Args:
            request: Incoming request

        Returns:
            API key if found, None otherwise
        """
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header

        return None

    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key against configured keys.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        # Get valid API keys from settings
        valid_keys = settings.api_keys

        if not valid_keys:
            # If no keys configured, allow all (development mode)
            if settings.environment == "development":
                return True
            return False

        # Check if provided key is in valid keys list
        return api_key in valid_keys


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Note: For production, use Redis-based rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # IP -> (count, reset_time)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and check rate limits.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from next handler or rate limit error
        """
        # Skip rate limiting for health checks
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host

        # Check rate limit (simplified - should use sliding window in production)
        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": "60"},
            )

        # Continue to next middleware/handler
        response = await call_next(request)
        return response

    def _is_rate_limited(self, ip: str) -> bool:
        """
        Check if IP is rate limited.

        Args:
            ip: Client IP address

        Returns:
            True if rate limited, False otherwise
        """
        import time

        current_time = time.time()

        if ip not in self.request_counts:
            self.request_counts[ip] = (1, current_time + 60)
            return False

        count, reset_time = self.request_counts[ip]

        # Reset if window expired
        if current_time >= reset_time:
            self.request_counts[ip] = (1, current_time + 60)
            return False

        # Increment counter
        if count >= self.requests_per_minute:
            return True

        self.request_counts[ip] = (count + 1, reset_time)
        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response information.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from next handler
        """
        import time

        # Log request
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response (in production, send to proper logging system)
        print(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s"
        )

        # Add custom headers
        response.headers["X-Process-Time"] = str(duration)

        return response
