"""
Security Headers Middleware

Adds security headers to all HTTP responses for protection against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

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

    async def dispatch(self, request: Request, call_next):
        """Log potential CORS violations"""
        origin = request.headers.get("origin")

        # Log requests from unexpected origins (potential security issue)
        if origin and not self._is_allowed_origin(origin):
            logger.warning(
                f"Request from unauthorized origin: {origin} "
                f"to {request.url.path} from {request.client.host if request.client else 'unknown'}"
            )

        response = await call_next(request)
        return response

    def _is_allowed_origin(self, origin: str) -> bool:
        """
        Check if origin is allowed.

        In production, this should check against your configured allowed origins.
        For now, we'll log all cross-origin requests for monitoring.
        """
        # Localhost and same-origin are always allowed
        if (
            origin.startswith("http://localhost")
            or origin.startswith("http://127.0.0.1")
            or origin.startswith("https://vulnzero.com")
            or origin.startswith("https://app.vulnzero.com")
        ):
            return True

        return False
