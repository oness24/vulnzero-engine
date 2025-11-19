"""
Security Headers Middleware

Adds security headers to all HTTP responses for protection against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

from shared.config.settings import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers Added:
    - X-Content-Type-Options: Prevents MIME-sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: XSS filter for older browsers
    - Strict-Transport-Security: Forces HTTPS
    - Content-Security-Policy: Restricts resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers to response"""
        response: Response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS for 1 year (31536000 seconds)
        # includeSubDomains: Apply to all subdomains
        # preload: Allow inclusion in browser HSTS preload lists
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Content Security Policy
        # default-src 'self': Only load resources from same origin
        # script-src: Allow scripts from self and inline (needed for some frameworks)
        # style-src: Allow styles from self and inline
        # img-src: Allow images from self and data URIs
        # font-src: Allow fonts from self
        # connect-src: Allow AJAX/WebSocket to self
        # frame-ancestors 'none': Prevent embedding (similar to X-Frame-Options)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        # Disable potentially dangerous browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Cache control for sensitive data
        # Only apply to API endpoints, not static assets
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security logging.

    While FastAPI's CORSMiddleware handles the actual CORS logic,
    this middleware adds security logging for CORS violations.
    """

    def __init__(self, app):
        """
        Initialize CORS security middleware.

        Loads allowed origins from application settings.
        """
        super().__init__(app)
        # Load allowed origins from configuration
        self.allowed_origins = set(settings.cors_origins_list)
        logger.info(f"CORSSecurityMiddleware initialized with {len(self.allowed_origins)} allowed origins")

    async def dispatch(self, request: Request, call_next):
        """Log potential CORS violations"""
        origin = request.headers.get("origin")

        # Log requests from unexpected origins (potential security issue)
        if origin and not self._is_allowed_origin(origin):
            logger.warning(
                f"Request from unauthorized origin: {origin} "
                f"to {request.url.path} from {request.client.host if request.client else 'unknown'}",
                extra={
                    "origin": origin,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                    "allowed_origins": list(self.allowed_origins)[:5]  # Log first 5 for debugging
                }
            )

        response = await call_next(request)
        return response

    def _is_allowed_origin(self, origin: str) -> bool:
        """
        Check if origin is allowed using exact match.

        Uses configured CORS origins from settings instead of hardcoded values.
        Performs exact string matching for security (not prefix matching).

        Args:
            origin: Origin header value from request

        Returns:
            True if origin is in allowed list, False otherwise
        """
        # Exact match against configured origins
        return origin in self.allowed_origins
