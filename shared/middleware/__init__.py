"""
Shared middleware modules for VulnZero
"""

from shared.middleware.security_headers import SecurityHeadersMiddleware

__all__ = ["SecurityHeadersMiddleware"]
