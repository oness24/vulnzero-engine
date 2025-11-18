"""
Middleware modules for VulnZero API
"""

from api.middleware.audit import AuditLogMiddleware

__all__ = ["AuditLogMiddleware"]
