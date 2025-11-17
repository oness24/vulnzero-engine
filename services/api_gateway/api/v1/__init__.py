"""
VulnZero API - Version 1
Main API router that includes all endpoint routers
"""

from fastapi import APIRouter

from services.api_gateway.api.v1.endpoints import (
    auth,
    vulnerabilities,
    assets,
    patches,
    deployments,
    system,
)

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(vulnerabilities.router, prefix="/vulnerabilities", tags=["Vulnerabilities"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(patches.router, prefix="/patches", tags=["Patches"])
api_router.include_router(deployments.router, prefix="/deployments", tags=["Deployments"])
api_router.include_router(system.router, prefix="/system", tags=["System"])

__all__ = ["api_router"]
