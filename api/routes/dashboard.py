"""
API routes for dashboard and statistics
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from datetime import datetime, timedelta

from shared.database.session import get_db
from shared.models.models import (
    Vulnerability,
    Patch,
    Deployment,
    Asset,
    VulnerabilitySeverity,
    PatchStatus,
    DeploymentStatus,
)
from services.monitoring.alerts import AlertManager
from services.monitoring.deployment_analytics import DeploymentAnalytics
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

alert_manager = AlertManager()
deployment_analytics = DeploymentAnalytics()


# Pydantic schemas
class DashboardStatsResponse(BaseModel):
    vulnerabilities: Dict[str, Any]
    patches: Dict[str, Any]
    deployments: Dict[str, Any]
    assets: Dict[str, Any]
    alerts: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]


class SystemHealthResponse(BaseModel):
    overall_status: str
    active_deployments: int
    active_alerts: int
    critical_vulnerabilities: int
    asset_health: Dict[str, Any]


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    hours: int = Query(24, description="Time period for recent stats"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive dashboard statistics
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Vulnerability stats
        vuln_total = await db.execute(select(func.count(Vulnerability.id)))
        vuln_count = vuln_total.scalar()

        vuln_by_severity = await db.execute(
            select(
                Vulnerability.severity,
                func.count(Vulnerability.id),
            ).group_by(Vulnerability.severity)
        )
        vuln_severity_dist = {sev: count for sev, count in vuln_by_severity.all()}

        vuln_recent = await db.execute(
            select(func.count(Vulnerability.id)).where(
                Vulnerability.created_at >= cutoff
            )
        )
        vuln_recent_count = vuln_recent.scalar()

        vulnerability_stats = {
            "total": vuln_count,
            "by_severity": vuln_severity_dist,
            "recent": vuln_recent_count,
            "critical": vuln_severity_dist.get("critical", 0),
            "high": vuln_severity_dist.get("high", 0),
        }

        # Patch stats
        patch_total = await db.execute(select(func.count(Patch.id)))
        patch_count = patch_total.scalar()

        patch_by_status = await db.execute(
            select(
                Patch.status,
                func.count(Patch.id),
            ).group_by(Patch.status)
        )
        patch_status_dist = {status: count for status, count in patch_by_status.all()}

        patch_avg_confidence = await db.execute(
            select(func.avg(Patch.confidence_score))
        )
        avg_confidence = patch_avg_confidence.scalar() or 0.0

        patch_stats = {
            "total": patch_count,
            "by_status": patch_status_dist,
            "average_confidence": float(avg_confidence),
            "pending": patch_status_dist.get(PatchStatus.PENDING.value, 0),
            "approved": patch_status_dist.get(PatchStatus.APPROVED.value, 0),
            "deployed": patch_status_dist.get(PatchStatus.DEPLOYED.value, 0),
        }

        # Deployment stats
        deploy_total = await db.execute(select(func.count(Deployment.id)))
        deploy_count = deploy_total.scalar()

        deploy_recent = await db.execute(
            select(func.count(Deployment.id)).where(
                Deployment.created_at >= cutoff
            )
        )
        deploy_recent_count = deploy_recent.scalar()

        deploy_by_status = await db.execute(
            select(
                Deployment.status,
                func.count(Deployment.id),
            ).where(
                Deployment.created_at >= cutoff
            ).group_by(Deployment.status)
        )
        deploy_status_dist = {status: count for status, count in deploy_by_status.all()}

        # Calculate success rate
        completed = deploy_status_dist.get(DeploymentStatus.COMPLETED.value, 0)
        failed = deploy_status_dist.get(DeploymentStatus.FAILED.value, 0)
        success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0.0

        deployment_stats = {
            "total": deploy_count,
            "recent": deploy_recent_count,
            "by_status": deploy_status_dist,
            "success_rate": success_rate,
            "active": deploy_status_dist.get(DeploymentStatus.IN_PROGRESS.value, 0),
        }

        # Asset stats
        asset_total = await db.execute(select(func.count(Asset.id)))
        asset_count = asset_total.scalar()

        asset_by_status = await db.execute(
            select(
                Asset.status,
                func.count(Asset.id),
            ).group_by(Asset.status)
        )
        asset_status_dist = {status: count for status, count in asset_by_status.all()}

        asset_stats = {
            "total": asset_count,
            "by_status": asset_status_dist,
            "active": asset_status_dist.get("active", 0),
        }

        # Alert stats
        alert_summary = alert_manager.get_alert_summary(hours=hours)

        # Recent activity
        recent_vulns = await db.execute(
            select(Vulnerability).order_by(desc(Vulnerability.created_at)).limit(5)
        )
        recent_deploys = await db.execute(
            select(Deployment).order_by(desc(Deployment.created_at)).limit(5)
        )

        recent_activity = []

        for vuln in recent_vulns.scalars().all():
            recent_activity.append({
                "type": "vulnerability",
                "id": vuln.id,
                "title": vuln.title,
                "cve_id": vuln.cve_id,
                "severity": vuln.severity,
                "timestamp": vuln.created_at.isoformat(),
            })

        for deploy in recent_deploys.scalars().all():
            recent_activity.append({
                "type": "deployment",
                "id": deploy.id,
                "patch_id": deploy.patch_id,
                "status": deploy.status,
                "strategy": deploy.strategy,
                "timestamp": deploy.created_at.isoformat(),
            })

        # Sort by timestamp
        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_activity = recent_activity[:10]

        return {
            "vulnerabilities": vulnerability_stats,
            "patches": patch_stats,
            "deployments": deployment_stats,
            "assets": asset_stats,
            "alerts": alert_summary,
            "recent_activity": recent_activity,
        }

    except Exception as e:
        logger.error("get_dashboard_stats_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
):
    """
    Get overall system health status
    """
    try:
        # Active deployments
        active_deploys = await db.execute(
            select(func.count(Deployment.id)).where(
                Deployment.status == DeploymentStatus.IN_PROGRESS
            )
        )
        active_deploy_count = active_deploys.scalar()

        # Active alerts
        active_alerts = alert_manager.get_active_alerts()
        active_alert_count = len(active_alerts)

        # Critical alerts
        critical_alerts = [a for a in active_alerts if a.get("severity") == "critical"]
        critical_alert_count = len(critical_alerts)

        # Critical vulnerabilities
        critical_vulns = await db.execute(
            select(func.count(Vulnerability.id)).where(
                Vulnerability.severity == VulnerabilitySeverity.CRITICAL
            )
        )
        critical_vuln_count = critical_vulns.scalar()

        # Asset health (simplified)
        total_assets = await db.execute(select(func.count(Asset.id)))
        total_asset_count = total_assets.scalar()

        active_assets = await db.execute(
            select(func.count(Asset.id)).where(Asset.status == "active")
        )
        active_asset_count = active_assets.scalar()

        asset_health = {
            "total": total_asset_count,
            "active": active_asset_count,
            "health_percentage": (active_asset_count / total_asset_count * 100) if total_asset_count > 0 else 0,
        }

        # Determine overall status
        overall_status = "healthy"

        if critical_alert_count > 0 or critical_vuln_count > 5:
            overall_status = "critical"
        elif active_alert_count > 10 or active_deploy_count > 5:
            overall_status = "warning"

        return {
            "overall_status": overall_status,
            "active_deployments": active_deploy_count,
            "active_alerts": active_alert_count,
            "critical_vulnerabilities": critical_vuln_count,
            "asset_health": asset_health,
        }

    except Exception as e:
        logger.error("get_system_health_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trend data for charts
    """
    try:
        from datetime import date

        trends = {
            "vulnerabilities": [],
            "patches": [],
            "deployments": [],
        }

        # Generate daily data points
        for i in range(days):
            day_start = datetime.utcnow() - timedelta(days=i+1)
            day_end = datetime.utcnow() - timedelta(days=i)

            # Vulnerabilities discovered
            vuln_count = await db.execute(
                select(func.count(Vulnerability.id)).where(
                    Vulnerability.created_at >= day_start,
                    Vulnerability.created_at < day_end,
                )
            )

            # Patches created
            patch_count = await db.execute(
                select(func.count(Patch.id)).where(
                    Patch.created_at >= day_start,
                    Patch.created_at < day_end,
                )
            )

            # Deployments
            deploy_count = await db.execute(
                select(func.count(Deployment.id)).where(
                    Deployment.created_at >= day_start,
                    Deployment.created_at < day_end,
                )
            )

            day_label = day_start.strftime("%Y-%m-%d")

            trends["vulnerabilities"].insert(0, {
                "date": day_label,
                "count": vuln_count.scalar(),
            })

            trends["patches"].insert(0, {
                "date": day_label,
                "count": patch_count.scalar(),
            })

            trends["deployments"].insert(0, {
                "date": day_label,
                "count": deploy_count.scalar(),
            })

        return trends

    except Exception as e:
        logger.error("get_trends_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-vulnerabilities")
async def get_top_vulnerabilities(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top vulnerabilities by priority
    """
    try:
        result = await db.execute(
            select(Vulnerability)
            .order_by(desc(Vulnerability.priority_score))
            .limit(limit)
        )

        vulnerabilities = result.scalars().all()

        return {
            "total": len(vulnerabilities),
            "vulnerabilities": [
                {
                    "id": v.id,
                    "cve_id": v.cve_id,
                    "title": v.title,
                    "severity": v.severity,
                    "cvss_score": v.cvss_score,
                    "priority_score": v.priority_score,
                    "affected_systems": len(v.affected_systems),
                }
                for v in vulnerabilities
            ],
        }

    except Exception as e:
        logger.error("get_top_vulnerabilities_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployment-analytics")
async def get_deployment_dashboard_analytics(
    hours: int = Query(24),
):
    """
    Get deployment analytics for dashboard
    """
    try:
        stats = await deployment_analytics.get_deployment_stats(hours=hours)
        performance = await deployment_analytics.get_performance_metrics(hours=hours)
        failure_analysis = await deployment_analytics.get_failure_analysis(hours=hours)

        return {
            "statistics": stats,
            "performance": performance,
            "failures": failure_analysis,
        }

    except Exception as e:
        logger.error("get_deployment_dashboard_analytics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get quick summary for dashboard header
    """
    try:
        # Quick counts
        vuln_count = (await db.execute(select(func.count(Vulnerability.id)))).scalar()
        patch_count = (await db.execute(select(func.count(Patch.id)))).scalar()
        deploy_count = (await db.execute(select(func.count(Deployment.id)))).scalar()
        asset_count = (await db.execute(select(func.count(Asset.id)))).scalar()

        # Active items
        active_deploys = (await db.execute(
            select(func.count(Deployment.id)).where(
                Deployment.status == DeploymentStatus.IN_PROGRESS
            )
        )).scalar()

        active_alerts = len(alert_manager.get_active_alerts())

        return {
            "vulnerabilities": vuln_count,
            "patches": patch_count,
            "deployments": deploy_count,
            "assets": asset_count,
            "active_deployments": active_deploys,
            "active_alerts": active_alerts,
        }

    except Exception as e:
        logger.error("get_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
