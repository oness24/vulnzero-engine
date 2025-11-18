"""
Audit logging middleware for VulnZero API

Logs all API requests and responses for security auditing and compliance.
"""

import uuid
import json
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
import structlog

logger = structlog.get_logger()


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests and responses for audit purposes

    Logs include:
    - Request ID (for tracing)
    - User information (if authenticated)
    - Request method, path, query parameters
    - Request body (excluding sensitive fields)
    - Response status code
    - Request duration
    - Client IP address
    - User agent
    """

    # Fields to redact from logs
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "api_key",
        "secret",
        "authorization",
        "cookie",
        "session",
    }

    # Paths to skip logging (e.g., health checks)
    SKIP_PATHS = {
        "/health",
        "/metrics",
        "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit information"""

        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Capture request time
        start_time = datetime.utcnow()

        # Extract request information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")

        # Get user information (if authenticated)
        user_id = getattr(request.state, "user_id", None)
        username = getattr(request.state, "username", None)

        # Read request body if present
        request_body = await self._get_request_body(request)

        # Log request
        logger.info(
            "audit_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id,
            username=username,
            timestamp=start_time.isoformat(),
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            # Log response
            logger.info(
                "audit_response",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_id=user_id,
                username=username,
                timestamp=end_time.isoformat(),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Log exception
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(
                "audit_exception",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                user_id=user_id,
                username=username,
                timestamp=end_time.isoformat(),
                exc_info=True,
            )

            # Re-raise the exception
            raise

    async def _get_request_body(self, request: Request) -> dict:
        """
        Safely get request body and redact sensitive fields

        Returns:
            dict: Request body with sensitive fields redacted
        """
        try:
            # Only log body for specific content types
            content_type = request.headers.get("Content-Type", "")

            if "application/json" in content_type:
                # Read body
                body = await request.body()

                if body:
                    try:
                        # Parse JSON
                        body_json = json.loads(body)

                        # Redact sensitive fields
                        redacted_body = self._redact_sensitive_data(body_json)

                        return redacted_body
                    except json.JSONDecodeError:
                        return {"_error": "Invalid JSON"}

            return {}

        except Exception as e:
            logger.warning(f"Error reading request body: {e}")
            return {}

    def _redact_sensitive_data(self, data: dict) -> dict:
        """
        Recursively redact sensitive fields from data

        Args:
            data: Dictionary to redact

        Returns:
            dict: Data with sensitive fields redacted
        """
        if not isinstance(data, dict):
            return data

        redacted = {}

        for key, value in data.items():
            # Check if field name contains sensitive terms
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                # Recursively redact nested dictionaries
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, list):
                # Handle lists
                redacted[key] = [
                    self._redact_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request

        Checks X-Forwarded-For header for proxy/load balancer scenarios

        Args:
            request: FastAPI request object

        Returns:
            str: Client IP address
        """
        # Check X-Forwarded-For header (for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "Unknown"
