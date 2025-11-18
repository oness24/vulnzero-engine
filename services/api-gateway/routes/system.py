"""
System and health check routes
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from shared.models.database import get_db
from shared.models.models import Vulnerability, Deployment, Patch, VulnerabilityStatus, DeploymentStatus
from shared.models.schemas import HealthResponse, MetricsResponse
from services.api_gateway.auth import get_current_active_user

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint

    Returns:
        HealthResponse: Service health status
    """
    services = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"

    # Check Redis
    try:
        import redis
        from shared.config.settings import settings
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_client.close()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"

    # Check Celery
    try:
        from shared.celery_app import app as celery_app
        # Check broker connection
        celery_app.connection().ensure_connection(max_retries=1, timeout=2)
        services["celery"] = "healthy"
    except Exception:
        services["celery"] = "unhealthy"

    # Determine overall status
    overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "degraded"

    return {
        "status": overall_status,
        "version": "0.1.0",
        "timestamp": datetime.utcnow(),
        "services": services,
    }


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get platform metrics

    Returns:
        MetricsResponse: Platform metrics
    """
    # Count vulnerabilities scanned
    vuln_query = select(func.count()).select_from(Vulnerability)
    result = await db.execute(vuln_query)
    vulnerabilities_scanned = result.scalar() or 0

    # Count patches generated
    patch_query = select(func.count()).select_from(Patch)
    result = await db.execute(patch_query)
    patches_generated = result.scalar() or 0

    # Count successful deployments
    deployment_query = (
        select(func.count())
        .select_from(Deployment)
        .where(Deployment.status == DeploymentStatus.SUCCESS)
    )
    result = await db.execute(deployment_query)
    deployments_completed = result.scalar() or 0

    # Calculate remediation rate
    remediated_query = (
        select(func.count())
        .select_from(Vulnerability)
        .where(Vulnerability.status == VulnerabilityStatus.REMEDIATED)
    )
    result = await db.execute(remediated_query)
    remediated = result.scalar() or 0
    remediation_rate = (remediated / vulnerabilities_scanned * 100) if vulnerabilities_scanned > 0 else 0

    # Calculate average time to remediate (in hours)
    time_query = select(
        Vulnerability.discovered_at,
        Vulnerability.remediated_at
    ).where(
        Vulnerability.remediated_at.isnot(None)
    )
    result = await db.execute(time_query)
    remediated_vulns = result.all()

    avg_time_to_remediate = 0.0
    if remediated_vulns:
        total_hours = 0.0
        for discovered_at, remediated_at in remediated_vulns:
            time_diff = remediated_at - discovered_at
            total_hours += time_diff.total_seconds() / 3600
        avg_time_to_remediate = round(total_hours / len(remediated_vulns), 2)

    return {
        "vulnerabilities_scanned": vulnerabilities_scanned,
        "patches_generated": patches_generated,
        "deployments_completed": deployments_completed,
        "remediation_rate": round(remediation_rate, 2),
        "avg_time_to_remediate": avg_time_to_remediate,
    }
