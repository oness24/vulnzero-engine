"""
Security Headers Middleware

Adds comprehensive security headers to all HTTP responses to protect against
common web vulnerabilities.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Headers added:
    - Content-Security-Policy: Prevents XSS, clickjacking, and code injection
    - Strict-Transport-Security: Enforces HTTPS connections
    - X-Frame-Options: Prevents clickjacking attacks
    - X-Content-Type-Options: Prevents MIME-sniffing
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    """

    def __init__(self, app, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Content Security Policy - Restricts resource loading
        # Allow same-origin by default, with specific exceptions for development
        if self.is_production:
            # Production: Strict CSP
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "  # unsafe-inline needed for some CSS frameworks
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # Development: More permissive CSP for hot reload, etc.
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # unsafe-eval needed for dev tools
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https: http:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*; "  # WebSocket for dev
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        response.headers["Content-Security-Policy"] = csp

        # Strict-Transport-Security - Force HTTPS (only in production)
        # max-age: 1 year, includeSubDomains: apply to all subdomains, preload: submit to HSTS preload list
        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # X-Frame-Options - Prevent clickjacking
        # DENY: Page cannot be displayed in a frame
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options - Prevent MIME sniffing
        # nosniff: Browser should not try to MIME-sniff
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy - Control referrer information
        # strict-origin-when-cross-origin: Send full URL for same-origin, only origin for cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy - Control browser features
        # Disable potentially dangerous features
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

        # X-XSS-Protection - Legacy XSS protection (for older browsers)
        # 1; mode=block: Enable XSS filter and block page if attack detected
        # Note: Modern browsers use CSP instead, but this helps older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # X-Permitted-Cross-Domain-Policies - Restrict Adobe Flash/PDF cross-domain requests
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        return response
