"""
API routes package
"""

from api.routes import (
    vulnerabilities,
    patches,
    deployments,
    monitoring,
    websocket,
    dashboard,
)

__all__ = [
    "vulnerabilities",
    "patches",
    "deployments",
    "monitoring",
    "websocket",
    "dashboard",
]
