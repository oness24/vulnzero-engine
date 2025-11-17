"""
VulnZero API Gateway - Pydantic Schemas
Request/Response models for API endpoints
"""

from services.api_gateway.schemas.common import (
    ErrorResponse,
    SuccessResponse,
    PaginationParams,
    PaginatedResponse,
)
from services.api_gateway.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from services.api_gateway.schemas.vulnerability import (
    VulnerabilityBase,
    VulnerabilityCreate,
    VulnerabilityUpdate,
    VulnerabilityResponse,
    VulnerabilityList,
)
from services.api_gateway.schemas.asset import (
    AssetBase,
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetList,
)
from services.api_gateway.schemas.patch import (
    PatchBase,
    PatchCreate,
    PatchUpdate,
    PatchResponse,
    PatchList,
)
from services.api_gateway.schemas.deployment import (
    DeploymentBase,
    DeploymentCreate,
    DeploymentUpdate,
    DeploymentResponse,
    DeploymentList,
)

__all__ = [
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "PaginatedResponse",
    "LoginRequest",
    "LoginResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "VulnerabilityBase",
    "VulnerabilityCreate",
    "VulnerabilityUpdate",
    "VulnerabilityResponse",
    "VulnerabilityList",
    "AssetBase",
    "AssetCreate",
    "AssetUpdate",
    "AssetResponse",
    "AssetList",
    "PatchBase",
    "PatchCreate",
    "PatchUpdate",
    "PatchResponse",
    "PatchList",
    "DeploymentBase",
    "DeploymentCreate",
    "DeploymentUpdate",
    "DeploymentResponse",
    "DeploymentList",
]
