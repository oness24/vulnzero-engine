"""
API Gateway routes
"""

from services.api_gateway.routes.auth import router as auth_router
from services.api_gateway.routes.vulnerabilities import router as vulnerabilities_router
from services.api_gateway.routes.assets import router as assets_router
from services.api_gateway.routes.patches import router as patches_router
from services.api_gateway.routes.deployments import router as deployments_router
from services.api_gateway.routes.system import router as system_router

__all__ = [
    "auth_router",
    "vulnerabilities_router",
    "assets_router",
    "patches_router",
    "deployments_router",
    "system_router",
]
