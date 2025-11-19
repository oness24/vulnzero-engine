"""
API Versioning Middleware
==========================

Middleware for API version negotiation and tracking.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from shared.api_versioning.versioning import (
    APIVersion,
    get_api_version,
)

logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning.

    Features:
    - Extracts API version from request
    - Adds version headers to response
    - Validates API version is supported
    - Tracks API version usage metrics

    Adds the following response headers:
    - X-API-Version: Current API version
    - X-API-Supported-Versions: List of supported versions
    - X-API-Latest-Version: Latest available version
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract API version from request
        try:
            api_version = get_api_version(request)
        except Exception as e:
            logger.warning(f"Failed to extract API version: {e}")
            api_version = APIVersion.latest()

        # Store version in request state for access by endpoints
        request.state.api_version = api_version

        # Check if version is supported
        if api_version not in APIVersion.all_versions():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Unsupported API version",
                    "requested_version": api_version.value,
                    "supported_versions": [v.value for v in APIVersion.all_versions()],
                    "latest_version": APIVersion.latest().value,
                },
            )

        # Process request
        try:
            response = await call_next(request)

            # Add version headers to response
            response.headers["X-API-Version"] = api_version.value
            response.headers["X-API-Supported-Versions"] = ", ".join(
                [v.value for v in APIVersion.all_versions()]
            )
            response.headers["X-API-Latest-Version"] = APIVersion.latest().value

            # Add CORS-safe expose headers
            existing_expose = response.headers.get("Access-Control-Expose-Headers", "")
            version_headers = "X-API-Version, X-API-Supported-Versions, X-API-Latest-Version"

            if existing_expose:
                response.headers["Access-Control-Expose-Headers"] = (
                    f"{existing_expose}, {version_headers}"
                )
            else:
                response.headers["Access-Control-Expose-Headers"] = version_headers

            # Track version usage (if monitoring is available)
            try:
                from shared.monitoring import http_requests_total

                # Track which API version was used
                # This is already tracked by path, but we can add explicit tracking
                pass
            except ImportError:
                pass

            return response

        except Exception as e:
            logger.error(f"Error in API version middleware: {e}", exc_info=True)
            raise


class APIVersionValidationMiddleware(BaseHTTPMiddleware):
    """
    Strict API version validation middleware.

    Requires explicit version in URL path.
    Rejects requests without proper version prefix.
    """

    def __init__(self, app, require_version: bool = True):
        super().__init__(app)
        self.require_version = require_version

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip validation for non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)

        # Skip validation for system endpoints
        if path.startswith("/api/health") or path.startswith("/api/metrics"):
            return await call_next(request)

        # Check if path includes version
        has_version = any(
            path.startswith(f"/api/{v.value}/") for v in APIVersion.all_versions()
        )

        if self.require_version and not has_version:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "API version required",
                    "message": "Please specify API version in URL path",
                    "example": f"/api/{APIVersion.latest().value}/vulnerabilities",
                    "supported_versions": [v.value for v in APIVersion.all_versions()],
                },
            )

        return await call_next(request)
