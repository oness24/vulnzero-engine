"""
Metrics Middleware
==================

Automatic Prometheus metrics collection for HTTP requests.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import logging

from shared.monitoring import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_request_size_bytes,
    http_response_size_bytes,
    http_errors_total,
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect Prometheus metrics for HTTP requests.

    Metrics collected:
    - Request count (by method, endpoint, status code)
    - Request duration (by method, endpoint)
    - Requests in progress (by method, endpoint)
    - Request/response sizes
    - Error count (by method, endpoint, error type)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """
        Process request and collect metrics.
        """
        # Extract route pattern for better metric labeling
        method = request.method
        endpoint = self._get_endpoint(request)

        # Track request size if available
        if "content-length" in request.headers:
            try:
                size = int(request.headers["content-length"])
                http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(size)
            except (ValueError, TypeError):
                pass

        # Increment in-progress counter
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Start timer
        start_time = time.time()

        try:
            # Process request
            response: Response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            status_code = response.status_code

            # Request count
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            # Request duration
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Response size if available
            if "content-length" in response.headers:
                try:
                    size = int(response.headers["content-length"])
                    http_response_size_bytes.labels(
                        method=method,
                        endpoint=endpoint
                    ).observe(size)
                except (ValueError, TypeError):
                    pass

            # Track errors (4xx, 5xx)
            if status_code >= 400:
                error_type = self._classify_error(status_code)
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    error_type=error_type
                ).inc()

            return response

        except Exception as e:
            # Record exception metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            http_errors_total.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(e).__name__
            ).inc()

            # Re-raise exception
            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

    @staticmethod
    def _get_endpoint(request: Request) -> str:
        """
        Extract endpoint pattern from request.

        Tries to get the route pattern, falls back to path.
        """
        # Try to get route pattern
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # Fall back to path, but sanitize
        path = request.url.path

        # Skip health checks to reduce noise
        if path in ["/health", "/health/live", "/health/ready"]:
            return path

        # For API endpoints, try to extract pattern
        if path.startswith("/api/v1/"):
            parts = path.split("/")
            # Replace UUIDs and IDs with placeholders
            sanitized_parts = []
            for part in parts:
                # Check if looks like UUID or numeric ID
                if len(part) == 36 and "-" in part:  # UUID
                    sanitized_parts.append("{id}")
                elif part.isdigit():  # Numeric ID
                    sanitized_parts.append("{id}")
                else:
                    sanitized_parts.append(part)
            return "/".join(sanitized_parts)

        return path

    @staticmethod
    def _classify_error(status_code: int) -> str:
        """
        Classify error by status code.

        Returns error type label for metrics.
        """
        if status_code == 400:
            return "bad_request"
        elif status_code == 401:
            return "unauthorized"
        elif status_code == 403:
            return "forbidden"
        elif status_code == 404:
            return "not_found"
        elif status_code == 422:
            return "validation_error"
        elif status_code == 429:
            return "rate_limit"
        elif 400 <= status_code < 500:
            return "client_error"
        elif status_code == 500:
            return "internal_error"
        elif status_code == 502:
            return "bad_gateway"
        elif status_code == 503:
            return "service_unavailable"
        elif status_code == 504:
            return "gateway_timeout"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown"
