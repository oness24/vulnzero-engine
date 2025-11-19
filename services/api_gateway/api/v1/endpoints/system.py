"""
VulnZero API Gateway - System Endpoints
Health checks and metrics
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session
import time
import logging

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    summary="System Health Check",
    description="Check the health status of the API and its dependencies.",
)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Returns the health status of the API and its dependencies.
    """
    from shared.config.database import engine

    # Check database connection
    db_healthy = True
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
    except Exception as e:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "api": "operational",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": time.time(),
        "version": "0.1.0",
    }


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Get Prometheus-formatted metrics for monitoring.",
    response_class=PlainTextResponse,
)
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns all application metrics in Prometheus format.

    Metrics include:
    - HTTP request metrics (count, duration, errors, in-progress)
    - Database metrics (queries, connection pool, slow queries)
    - Cache metrics (hits, misses, operations, memory)
    - Business metrics (vulnerabilities, patches, deployments)
    - Celery task metrics (tasks, duration, queue length, workers)
    - LLM API metrics (calls, tokens, duration)
    """
    # Update dynamic metrics before exporting
    try:
        from shared.monitoring import update_db_pool_metrics

        update_db_pool_metrics()
        # Cache and Celery metrics are updated via background tasks

    except Exception as e:
        logger.warning(f"Failed to update dynamic metrics: {e}")

    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get(
    "/info",
    summary="System Information",
    description="Get general system information.",
)
async def system_info(current_user: dict = Depends(get_current_user)):
    """Get system information"""
    from shared.config.settings import settings

    return {
        "application": "VulnZero API",
        "version": "0.1.0",
        "environment": settings.environment,
        "features": {
            "auto_remediation": settings.feature_auto_remediation,
            "digital_twin_testing": settings.feature_digital_twin_testing,
            "canary_deployments": settings.feature_canary_deployments,
            "ml_prioritization": settings.feature_ml_prioritization,
        },
    }


@router.get(
    "/deprecations",
    summary="API Deprecation Information",
    description="Get information about deprecated API endpoints and sunset dates.",
)
async def deprecations():
    """
    Get information about deprecated API endpoints.

    Returns:
        - List of deprecated endpoints
        - Sunset dates
        - Alternative endpoints
        - Current and supported API versions

    Use this endpoint to check if any endpoints you're using are deprecated
    and plan migrations accordingly.
    """
    from shared.api_versioning.versioning import (
        list_deprecated_endpoints,
        APIVersion,
    )

    # Get all deprecated endpoints
    deprecations = await list_deprecated_endpoints()

    return {
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
