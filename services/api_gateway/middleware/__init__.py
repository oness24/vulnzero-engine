"""
API Gateway Middleware Package

Contains custom middleware for the VulnZero API Gateway:
- Security Headers: Adds security headers to protect against common web vulnerabilities
- CORS Security: Logs and monitors cross-origin requests
"""

from services.api_gateway.middleware.security_headers import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware,
)

__all__ = [
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware",
]
