"""API versioning and deprecation management"""

from shared.api_versioning.versioning import (
    APIVersion,
    VersionedAPIRouter,
    get_api_version,
    deprecated,
    sunset,
)
from shared.api_versioning.middleware import (
    APIVersionMiddleware,
)

__all__ = [
    # Version management
    "APIVersion",
    "VersionedAPIRouter",
    "get_api_version",
    # Deprecation
    "deprecated",
    "sunset",
    # Middleware
    "APIVersionMiddleware",
]
