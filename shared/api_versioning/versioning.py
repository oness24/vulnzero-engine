"""
API Versioning System
=====================

URL-based API versioning with deprecation tracking and sunset dates.
"""

import logging
from datetime import datetime, date
from enum import Enum
from typing import Optional, Callable, List, Any
from functools import wraps

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class APIVersion(str, Enum):
    """Supported API versions"""

    V1 = "v1"
    V2 = "v2"  # For future use

    @classmethod
    def latest(cls) -> "APIVersion":
        """Get the latest API version"""
        return cls.V1

    @classmethod
    def all_versions(cls) -> List["APIVersion"]:
        """Get all supported versions"""
        return [cls.V1]


class DeprecationInfo(BaseModel):
    """
    Information about deprecated endpoints.

    Attributes:
        version: API version where endpoint is deprecated
        deprecated_at: Date when deprecation was announced
        sunset_at: Date when endpoint will be removed
        alternative: Suggested alternative endpoint
        reason: Reason for deprecation
    """

    version: str
    deprecated_at: date
    sunset_at: Optional[date] = None
    alternative: Optional[str] = None
    reason: Optional[str] = None


# Registry of deprecated endpoints
_deprecated_endpoints: dict[str, DeprecationInfo] = {}


def deprecated(
    sunset_date: Optional[date] = None,
    alternative: Optional[str] = None,
    reason: Optional[str] = None,
):
    """
    Decorator to mark an endpoint as deprecated.

    Adds deprecation headers to responses and logs warnings.

    Args:
        sunset_date: Date when endpoint will be removed (RFC 8594)
        alternative: Alternative endpoint to use
        reason: Reason for deprecation

    Usage:
        @app.get("/api/v1/old-endpoint")
        @deprecated(
            sunset_date=date(2025, 12, 31),
            alternative="/api/v2/new-endpoint",
            reason="Moved to v2 with improved schema"
        )
        async def old_endpoint():
            return {"message": "old"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Log deprecation warning
            logger.warning(
                f"Deprecated endpoint called: {func.__name__} "
                f"(sunset: {sunset_date}, alternative: {alternative})"
            )

            # Call original function
            result = await func(*args, **kwargs)

            # Add deprecation headers if result is a Response
            if hasattr(result, "headers"):
                result.headers["Deprecation"] = "true"
                result.headers["X-API-Deprecation-Info"] = (
                    f"This endpoint is deprecated. "
                    f"{f'Use {alternative} instead. ' if alternative else ''}"
                    f"{f'Reason: {reason}. ' if reason else ''}"
                    f"{f'Sunset: {sunset_date}' if sunset_date else ''}"
                )
                if sunset_date:
                    result.headers["Sunset"] = sunset_date.isoformat()

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Log deprecation warning
            logger.warning(
                f"Deprecated endpoint called: {func.__name__} "
                f"(sunset: {sunset_date}, alternative: {alternative})"
            )

            # Call original function
            result = func(*args, **kwargs)

            # Add deprecation headers if result is a Response
            if hasattr(result, "headers"):
                result.headers["Deprecation"] = "true"
                result.headers["X-API-Deprecation-Info"] = (
                    f"This endpoint is deprecated. "
                    f"{f'Use {alternative} instead. ' if alternative else ''}"
                    f"{f'Reason: {reason}. ' if reason else ''}"
                    f"{f'Sunset: {sunset_date}' if sunset_date else ''}"
                )
                if sunset_date:
                    result.headers["Sunset"] = sunset_date.isoformat()

            return result

        # Store deprecation info
        endpoint_path = f"{func.__module__}.{func.__name__}"
        _deprecated_endpoints[endpoint_path] = DeprecationInfo(
            version="v1",
            deprecated_at=date.today(),
            sunset_at=sunset_date,
            alternative=alternative,
            reason=reason,
        )

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def sunset(sunset_date: date):
    """
    Decorator to enforce sunset date for deprecated endpoints.

    Raises 410 Gone if sunset date has passed.

    Args:
        sunset_date: Date when endpoint was/will be removed

    Usage:
        @app.get("/api/v1/removed-endpoint")
        @sunset(date(2024, 1, 1))
        async def removed_endpoint():
            # This will return 410 Gone after sunset date
            return {"message": "removed"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if sunset date has passed
            if date.today() >= sunset_date:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail={
                        "error": "Endpoint has been sunset",
                        "sunset_date": sunset_date.isoformat(),
                        "message": f"This endpoint was removed on {sunset_date}",
                    },
                )

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check if sunset date has passed
            if date.today() >= sunset_date:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail={
                        "error": "Endpoint has been sunset",
                        "sunset_date": sunset_date.isoformat(),
                        "message": f"This endpoint was removed on {sunset_date}",
                    },
                )

            return func(*args, **kwargs)

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class VersionedAPIRouter(APIRouter):
    """
    Extended APIRouter with built-in version tracking.

    Automatically adds version prefix to all routes and tracks
    version-specific endpoints.

    Usage:
        router = VersionedAPIRouter(
            version=APIVersion.V1,
            prefix="/vulnerabilities",
            tags=["vulnerabilities"]
        )

        @router.get("/")
        async def list_vulnerabilities():
            # Available at /api/v1/vulnerabilities/
            return []
    """

    def __init__(
        self,
        version: APIVersion,
        *args,
        **kwargs,
    ):
        self.api_version = version

        # Add version to prefix if not already present
        prefix = kwargs.get("prefix", "")
        if not prefix.startswith(f"/api/{version.value}"):
            if prefix.startswith("/api/"):
                # Replace existing version
                prefix = f"/api/{version.value}" + prefix[4:]
            elif prefix.startswith("/"):
                prefix = f"/api/{version.value}" + prefix
            else:
                prefix = f"/api/{version.value}/" + prefix

        kwargs["prefix"] = prefix

        super().__init__(*args, **kwargs)

        logger.info(f"Created versioned router for {version.value}: {prefix}")


def get_api_version(request: Request) -> APIVersion:
    """
    Extract API version from request.

    Looks for version in:
    1. URL path (/api/v1/...)
    2. Accept header (Accept: application/vnd.vulnzero.v1+json)
    3. Custom header (X-API-Version: v1)
    4. Defaults to latest version

    Args:
        request: FastAPI request

    Returns:
        APIVersion extracted from request
    """
    # 1. Check URL path
    path = request.url.path
    for version in APIVersion.all_versions():
        if path.startswith(f"/api/{version.value}/"):
            return version

    # 2. Check Accept header
    accept = request.headers.get("Accept", "")
    for version in APIVersion.all_versions():
        if f"vnd.vulnzero.{version.value}" in accept:
            return version

    # 3. Check custom header
    version_header = request.headers.get("X-API-Version", "")
    try:
        return APIVersion(version_header.lower())
    except ValueError:
        pass

    # 4. Default to latest
    return APIVersion.latest()


async def list_deprecated_endpoints() -> dict[str, DeprecationInfo]:
    """
    Get list of all deprecated endpoints.

    Returns:
        Dictionary of deprecated endpoints with their info
    """
    return _deprecated_endpoints.copy()


async def check_sunset_endpoints() -> List[dict]:
    """
    Check for endpoints past their sunset date.

    Returns:
        List of endpoints that should be removed
    """
    today = date.today()
    sunset_endpoints = []

    for endpoint, info in _deprecated_endpoints.items():
        if info.sunset_at and info.sunset_at <= today:
            sunset_endpoints.append(
                {
                    "endpoint": endpoint,
                    "sunset_date": info.sunset_at.isoformat(),
                    "alternative": info.alternative,
                }
            )

    return sunset_endpoints


# Example usage for system endpoints
async def get_deprecation_info(request: Request) -> JSONResponse:
    """
    Endpoint to get information about deprecated APIs.

    Available at: /api/v1/system/deprecations

    Returns:
        List of deprecated endpoints with sunset dates and alternatives
    """
    deprecations = await list_deprecated_endpoints()

    response_data = {
        "deprecated_endpoints": [
            {
                "endpoint": endpoint,
                "version": info.version,
                "deprecated_at": info.deprecated_at.isoformat(),
                "sunset_at": info.sunset_at.isoformat() if info.sunset_at else None,
                "alternative": info.alternative,
                "reason": info.reason,
            }
            for endpoint, info in deprecations.items()
        ],
        "current_version": APIVersion.latest().value,
        "supported_versions": [v.value for v in APIVersion.all_versions()],
    }

    return JSONResponse(content=response_data)
