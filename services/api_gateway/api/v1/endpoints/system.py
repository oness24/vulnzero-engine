"""
VulnZero API Gateway - System Endpoints
Health checks and metrics
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from sqlalchemy.orm import Session
import time

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import get_current_user

router = APIRouter()

# Prometheus metrics
request_counter = Counter(
    "vulnzero_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "vulnzero_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"]
)


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
    Returns metrics in Prometheus format.
    """
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
