"""
API routes for monitoring and alerts
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime

from shared.database.session import get_db
from shared.models.models import Deployment
from services.monitoring.deployment_monitor import DeploymentMonitor
from services.monitoring.rollback_manager import RollbackManager
from services.monitoring.alerts import AlertManager, AlertSeverity, AlertChannel
from services.monitoring.deployment_analytics import DeploymentAnalytics
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Initialize monitoring components
deployment_monitor = DeploymentMonitor()
rollback_manager = RollbackManager()
alert_manager = AlertManager()
deployment_analytics = DeploymentAnalytics()


# Pydantic schemas
class HealthCheckResponse(BaseModel):
    deployment_id: int
    total_assets: int
    healthy_assets: int
    unhealthy_assets: int
    asset_health: dict


class MetricsResponse(BaseModel):
    deployment_id: int
    metrics: dict
    timestamp: datetime


class AlertResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    deployment_id: Optional[int]
    acknowledged: bool
    resolved: bool
    created_at: str


class AlertCreateRequest(BaseModel):
    title: str
    message: str
    severity: str = Field(..., description="info, warning, error, critical")
    deployment_id: Optional[int] = None


class NotificationChannelRequest(BaseModel):
    channel_type: str = Field(..., description="log, email, slack, pagerduty, webhook")
    config: dict


@router.get("/health/{deployment_id}", response_model=HealthCheckResponse)
async def check_deployment_health(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Check deployment health status
    """
    try:
        # Get deployment
        from sqlalchemy import select
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Get assets
        assets = deployment.results.get("assets", []) if deployment.results else []

        if not assets:
            return {
                "deployment_id": deployment_id,
                "total_assets": 0,
                "healthy_assets": 0,
                "unhealthy_assets": 0,
                "asset_health": {},
            }

        # Check health
        health_result = await deployment_monitor.check_deployment_health(
            deployment_id=deployment_id,
            assets=assets,
        )

        return health_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("check_deployment_health_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{deployment_id}")
async def get_deployment_metrics(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get deployment metrics
    """
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        assets = deployment.results.get("assets", []) if deployment.results else []

        # Collect metrics from all assets
        all_metrics = {}
        for asset in assets:
            metrics_result = await deployment_monitor.collect_metrics(asset)
            if metrics_result.get("success"):
                all_metrics[asset.get("name", str(asset.get("id")))] = metrics_result["metrics"]

        return {
            "deployment_id": deployment_id,
            "metrics": all_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_deployment_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring-status/{deployment_id}")
async def get_monitoring_status(
    deployment_id: int,
):
    """
    Get monitoring session status
    """
    try:
        status = deployment_monitor.get_monitoring_status(deployment_id)

        return status

    except Exception as e:
        logger.error("get_monitoring_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start-monitoring/{deployment_id}")
async def start_monitoring(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Start monitoring a deployment
    """
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Start monitoring session
        deployment_monitor.start_monitoring(deployment_id)

        # Trigger monitoring task
        from services.monitoring.tasks import monitor_deployment

        task = monitor_deployment.delay(deployment_id)

        return {
            "message": "Monitoring started",
            "deployment_id": deployment_id,
            "task_id": task.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("start_monitoring_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-monitoring/{deployment_id}")
async def stop_monitoring(
    deployment_id: int,
):
    """
    Stop monitoring a deployment
    """
    try:
        deployment_monitor.stop_monitoring(deployment_id)

        return {
            "message": "Monitoring stopped",
            "deployment_id": deployment_id,
        }

    except Exception as e:
        logger.error("stop_monitoring_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    deployment_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    active_only: bool = Query(True, description="Show only active (unresolved) alerts"),
):
    """
    List alerts with filtering
    """
    try:
        if active_only:
            min_severity = AlertSeverity(severity) if severity else None
            alerts = alert_manager.get_active_alerts(
                deployment_id=deployment_id,
                min_severity=min_severity,
            )
        else:
            alerts = alert_manager.alerts

            # Apply filters
            if deployment_id:
                alerts = [a for a in alerts if a.get("deployment_id") == deployment_id]

            if severity:
                alerts = [a for a in alerts if a.get("severity") == severity]

        return alerts

    except Exception as e:
        logger.error("list_alerts_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreateRequest,
):
    """
    Create a new alert
    """
    try:
        severity = AlertSeverity(alert_data.severity)

        alert = alert_manager.create_alert(
            title=alert_data.title,
            message=alert_data.message,
            severity=severity,
            deployment_id=alert_data.deployment_id,
        )

        return alert

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid severity: {str(e)}")
    except Exception as e:
        logger.error("create_alert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
):
    """
    Acknowledge an alert
    """
    try:
        result = alert_manager.acknowledge_alert(alert_id)

        if not result:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"message": "Alert acknowledged", "alert_id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("acknowledge_alert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
):
    """
    Resolve an alert
    """
    try:
        result = alert_manager.resolve_alert(alert_id)

        if not result:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"message": "Alert resolved", "alert_id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("resolve_alert_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/summary")
async def get_alert_summary(
    hours: int = Query(24, description="Time period in hours"),
):
    """
    Get alert summary
    """
    try:
        summary = alert_manager.get_alert_summary(hours=hours)

        return summary

    except Exception as e:
        logger.error("get_alert_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification-channels")
async def add_notification_channel(
    channel_data: NotificationChannelRequest,
):
    """
    Add notification channel
    """
    try:
        channel_type = AlertChannel(channel_data.channel_type)

        result = alert_manager.add_notification_channel(
            channel_type=channel_type,
            config=channel_data.config,
        )

        return {
            "message": "Notification channel added",
            "channel_type": channel_data.channel_type,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid channel type: {str(e)}")
    except Exception as e:
        logger.error("add_notification_channel_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notification-channels/{channel_type}")
async def remove_notification_channel(
    channel_type: str,
):
    """
    Remove notification channel
    """
    try:
        result = alert_manager.remove_notification_channel(channel_type)

        if not result:
            raise HTTPException(status_code=404, detail="Channel not found")

        return {
            "message": "Notification channel removed",
            "channel_type": channel_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("remove_notification_channel_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rollback-triggers/{deployment_id}")
async def get_rollback_triggers(
    deployment_id: int,
):
    """
    Get rollback trigger status
    """
    try:
        status = rollback_manager.get_trigger_status(deployment_id)

        return status

    except Exception as e:
        logger.error("get_rollback_triggers_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rollback-history")
async def get_rollback_history(
    deployment_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Get rollback history
    """
    try:
        history = rollback_manager.get_rollback_history(deployment_id)

        # Apply limit
        history = history[:limit]

        return {
            "total": len(history),
            "history": history,
        }

    except Exception as e:
        logger.error("get_rollback_history_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/stats")
async def get_deployment_analytics(
    hours: int = Query(24, description="Time period in hours"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
):
    """
    Get deployment analytics
    """
    try:
        stats = await deployment_analytics.get_deployment_stats(
            hours=hours,
            strategy=strategy,
        )

        return stats

    except Exception as e:
        logger.error("get_deployment_analytics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/failure-analysis")
async def get_failure_analysis(
    hours: int = Query(24),
):
    """
    Get failure analysis
    """
    try:
        analysis = await deployment_analytics.get_failure_analysis(hours=hours)

        return analysis

    except Exception as e:
        logger.error("get_failure_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/performance")
async def get_performance_metrics(
    hours: int = Query(24),
):
    """
    Get performance metrics
    """
    try:
        metrics = await deployment_analytics.get_performance_metrics(hours=hours)

        return metrics

    except Exception as e:
        logger.error("get_performance_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/patch/{patch_id}")
async def get_patch_analytics(
    patch_id: int,
):
    """
    Get analytics for specific patch
    """
    try:
        stats = await deployment_analytics.get_patch_deployment_stats(patch_id)

        return stats

    except Exception as e:
        logger.error("get_patch_analytics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
