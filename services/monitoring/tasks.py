"""
Celery tasks for monitoring and rollback
"""

from typing import Dict, Any, List, Optional
from celery import shared_task
from shared.database.session import AsyncSessionLocal
from shared.models.models import Deployment, DeploymentStatus
from sqlalchemy import select
import structlog

from services.monitoring.deployment_monitor import DeploymentMonitor
from services.monitoring.rollback_manager import RollbackManager
from services.monitoring.alerts import AlertManager, AlertSeverity
from services.monitoring.deployment_analytics import DeploymentAnalytics

logger = structlog.get_logger()

# Global instances
deployment_monitor = DeploymentMonitor()
rollback_manager = RollbackManager()
alert_manager = AlertManager()
deployment_analytics = DeploymentAnalytics()


async def _monitor_deployment_async(
    deployment_id: int,
    check_interval: int = 30,
    max_duration: int = 3600,
) -> Dict[str, Any]:
    """
    Monitor deployment asynchronously

    Args:
        deployment_id: Deployment ID to monitor
        check_interval: Health check interval in seconds
        max_duration: Maximum monitoring duration in seconds

    Returns:
        Monitoring results
    """
    try:
        async with AsyncSessionLocal() as session:
            # Get deployment
            result = await session.execute(
                select(Deployment).where(Deployment.id == deployment_id)
            )
            deployment = result.scalar_one_or_none()

            if not deployment:
                logger.error("deployment_not_found", deployment_id=deployment_id)
                return {
                    "status": "error",
                    "message": f"Deployment {deployment_id} not found",
                }

            # Get assets from deployment results
            assets = deployment.results.get("assets", [])

            if not assets:
                logger.warning("no_assets_to_monitor", deployment_id=deployment_id)
                return {
                    "status": "error",
                    "message": "No assets found to monitor",
                }

            # Track monitoring start
            await deployment_analytics.track_deployment_start(
                deployment_id=deployment_id,
                patch_id=deployment.patch_id,
                strategy=deployment.strategy,
                asset_count=len(assets),
                metadata={"monitored": True},
            )

            # Create alert
            alert_manager.create_deployment_alert(
                deployment_id=deployment_id,
                alert_type="deployment_started",
                details={"asset_count": len(assets), "strategy": deployment.strategy},
            )

            # Monitor deployment
            monitoring_result = await deployment_monitor.monitor_deployment(
                deployment_id=deployment_id,
                assets=assets,
                check_interval=check_interval,
                max_duration=max_duration,
            )

            # Track completion
            success = monitoring_result.get("all_healthy", False)
            await deployment_analytics.track_deployment_completion(
                deployment_id=deployment_id,
                success=success,
                results=monitoring_result,
            )

            # Check if rollback is recommended
            if monitoring_result.get("rollback_recommended", False):
                logger.warning(
                    "rollback_recommended",
                    deployment_id=deployment_id,
                    reason=monitoring_result.get("rollback_reason"),
                )

                # Create alert
                alert_manager.create_deployment_alert(
                    deployment_id=deployment_id,
                    alert_type="rollback_triggered",
                    details={
                        "reason": monitoring_result.get("rollback_reason"),
                        "metrics": monitoring_result.get("metrics"),
                    },
                )

                # Trigger rollback task
                _rollback_deployment_async.delay(deployment_id)

            return {
                "status": "success",
                "deployment_id": deployment_id,
                "monitoring_result": monitoring_result,
            }

    except Exception as e:
        logger.error(
            "monitor_deployment_failed",
            deployment_id=deployment_id,
            error=str(e),
            exc_info=True,
        )

        # Create error alert
        alert_manager.create_deployment_alert(
            deployment_id=deployment_id,
            alert_type="health_check_failed",
            details={"error": str(e)},
        )

        return {
            "status": "error",
            "deployment_id": deployment_id,
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.monitor_deployment")
def monitor_deployment(
    self,
    deployment_id: int,
    check_interval: int = 30,
    max_duration: int = 3600,
) -> Dict[str, Any]:
    """
    Monitor deployment health

    Args:
        deployment_id: Deployment ID to monitor
        check_interval: Health check interval in seconds
        max_duration: Maximum monitoring duration in seconds

    Returns:
        Monitoring results
    """
    import asyncio
    return asyncio.run(_monitor_deployment_async(
        deployment_id,
        check_interval,
        max_duration,
    ))


async def _rollback_deployment_async(deployment_id: int) -> Dict[str, Any]:
    """
    Execute deployment rollback asynchronously

    Args:
        deployment_id: Deployment ID to rollback

    Returns:
        Rollback results
    """
    try:
        async with AsyncSessionLocal() as session:
            # Get deployment
            result = await session.execute(
                select(Deployment).where(Deployment.id == deployment_id)
            )
            deployment = result.scalar_one_or_none()

            if not deployment:
                return {
                    "status": "error",
                    "message": f"Deployment {deployment_id} not found",
                }

            # Get assets and rollback script
            assets = deployment.results.get("assets", [])
            rollback_script = deployment.patch.rollback_script if hasattr(deployment, 'patch') else None

            if not rollback_script:
                logger.error("no_rollback_script", deployment_id=deployment_id)
                return {
                    "status": "error",
                    "message": "No rollback script available",
                }

            # Execute rollback
            rollback_result = await rollback_manager.execute_rollback(
                deployment_id=deployment_id,
                assets=assets,
                rollback_script=rollback_script,
                reason="automatic_rollback",
            )

            # Track rollback
            await deployment_analytics.track_rollback(
                deployment_id=deployment_id,
                rollback_id=rollback_result.get("rollback_id", 0),
                reason="automatic_rollback",
                success=rollback_result.get("success", False),
                results=rollback_result,
            )

            # Update deployment status
            deployment.status = DeploymentStatus.ROLLED_BACK
            await session.commit()

            # Create alert
            if rollback_result.get("success"):
                alert_manager.create_deployment_alert(
                    deployment_id=deployment_id,
                    alert_type="rollback_completed",
                    details=rollback_result,
                )
            else:
                alert_manager.create_deployment_alert(
                    deployment_id=deployment_id,
                    alert_type="rollback_failed",
                    details=rollback_result,
                )

            return {
                "status": "success",
                "deployment_id": deployment_id,
                "rollback_result": rollback_result,
            }

    except Exception as e:
        logger.error(
            "rollback_failed",
            deployment_id=deployment_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "status": "error",
            "deployment_id": deployment_id,
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.rollback_deployment")
def rollback_deployment(self, deployment_id: int) -> Dict[str, Any]:
    """
    Rollback a deployment

    Args:
        deployment_id: Deployment ID to rollback

    Returns:
        Rollback results
    """
    import asyncio
    return asyncio.run(_rollback_deployment_async(deployment_id))


async def _check_deployment_health_async(deployment_id: int) -> Dict[str, Any]:
    """
    Check deployment health once

    Args:
        deployment_id: Deployment ID

    Returns:
        Health check results
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Deployment).where(Deployment.id == deployment_id)
            )
            deployment = result.scalar_one_or_none()

            if not deployment:
                return {
                    "status": "error",
                    "message": f"Deployment {deployment_id} not found",
                }

            assets = deployment.results.get("assets", [])

            # Perform health check
            health_result = await deployment_monitor.check_deployment_health(
                deployment_id=deployment_id,
                assets=assets,
            )

            # Check rollback triggers
            should_rollback = rollback_manager.check_rollback_triggers(
                deployment_id=deployment_id,
                health_results=health_result.get("asset_health", {}),
                metrics=health_result.get("metrics", {}),
            )

            if should_rollback:
                logger.warning(
                    "rollback_triggered",
                    deployment_id=deployment_id,
                )
                _rollback_deployment_async.delay(deployment_id)

            return {
                "status": "success",
                "deployment_id": deployment_id,
                "health": health_result,
                "rollback_triggered": should_rollback,
            }

    except Exception as e:
        logger.error(
            "health_check_failed",
            deployment_id=deployment_id,
            error=str(e),
        )
        return {
            "status": "error",
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.check_deployment_health")
def check_deployment_health(self, deployment_id: int) -> Dict[str, Any]:
    """
    Check deployment health

    Args:
        deployment_id: Deployment ID

    Returns:
        Health check results
    """
    import asyncio
    return asyncio.run(_check_deployment_health_async(deployment_id))


async def _generate_deployment_report_async(hours: int = 24) -> Dict[str, Any]:
    """
    Generate deployment report

    Args:
        hours: Number of hours to include in report

    Returns:
        Deployment report
    """
    try:
        # Get statistics
        stats = await deployment_analytics.get_deployment_stats(hours=hours)

        # Get failure analysis
        failure_analysis = await deployment_analytics.get_failure_analysis(hours=hours)

        # Get performance metrics
        performance = await deployment_analytics.get_performance_metrics(hours=hours)

        report = {
            "generated_at": deployment_analytics.deployment_history[-1]["started_at"] if deployment_analytics.deployment_history else None,
            "time_period_hours": hours,
            "statistics": stats,
            "failure_analysis": failure_analysis,
            "performance_metrics": performance,
        }

        logger.info(
            "deployment_report_generated",
            hours=hours,
            total_deployments=stats.get("total_deployments", 0),
        )

        return {
            "status": "success",
            "report": report,
        }

    except Exception as e:
        logger.error("report_generation_failed", error=str(e))
        return {
            "status": "error",
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.generate_deployment_report")
def generate_deployment_report(self, hours: int = 24) -> Dict[str, Any]:
    """
    Generate deployment report

    Args:
        hours: Number of hours to include

    Returns:
        Report data
    """
    import asyncio
    return asyncio.run(_generate_deployment_report_async(hours))


async def _cleanup_old_data_async(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old deployment data

    Args:
        days: Number of days to keep

    Returns:
        Cleanup results
    """
    try:
        # Clear old history
        cleared = await deployment_analytics.clear_old_history(days=days)

        # Clear old rollback history
        rollback_manager.clear_old_rollbacks(days=days)

        logger.info(
            "old_data_cleaned",
            days=days,
            records_cleared=cleared,
        )

        return {
            "status": "success",
            "records_cleared": cleared,
            "days": days,
        }

    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        return {
            "status": "error",
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.cleanup_old_data")
def cleanup_old_data(self, days: int = 30) -> Dict[str, Any]:
    """
    Clean up old deployment data

    Args:
        days: Number of days to keep

    Returns:
        Cleanup results
    """
    import asyncio
    return asyncio.run(_cleanup_old_data_async(days))


async def _check_all_active_deployments_async() -> Dict[str, Any]:
    """
    Check health of all active deployments

    Returns:
        Check results
    """
    try:
        async with AsyncSessionLocal() as session:
            # Get all in-progress deployments
            result = await session.execute(
                select(Deployment).where(
                    Deployment.status == DeploymentStatus.IN_PROGRESS
                )
            )
            deployments = result.scalars().all()

            checked = 0
            rollbacks_triggered = 0

            for deployment in deployments:
                health_result = await _check_deployment_health_async(deployment.id)
                checked += 1

                if health_result.get("rollback_triggered", False):
                    rollbacks_triggered += 1

            logger.info(
                "active_deployments_checked",
                total=checked,
                rollbacks_triggered=rollbacks_triggered,
            )

            return {
                "status": "success",
                "checked": checked,
                "rollbacks_triggered": rollbacks_triggered,
            }

    except Exception as e:
        logger.error("active_deployments_check_failed", error=str(e))
        return {
            "status": "error",
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.check_all_active_deployments")
def check_all_active_deployments(self) -> Dict[str, Any]:
    """
    Check health of all active deployments

    Returns:
        Check results
    """
    import asyncio
    return asyncio.run(_check_all_active_deployments_async())


async def _send_deployment_summary_async(
    hours: int = 24,
    recipients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Send deployment summary

    Args:
        hours: Number of hours to include
        recipients: Optional list of recipients

    Returns:
        Summary results
    """
    try:
        # Generate report
        stats = await deployment_analytics.get_deployment_stats(hours=hours)

        # Get alert summary
        alert_summary = alert_manager.get_alert_summary(hours=hours)

        # Create summary alert
        summary_message = f"""
Deployment Summary ({hours}h):
- Total Deployments: {stats['total_deployments']}
- Success Rate: {stats['success_rate']:.1f}%
- Rollback Rate: {stats['rollback_rate']:.1f}%
- Total Alerts: {alert_summary['total_alerts']}
- Active Alerts: {alert_summary['active_alerts']}
"""

        alert = alert_manager.create_alert(
            title=f"Deployment Summary ({hours}h)",
            message=summary_message.strip(),
            severity=AlertSeverity.INFO,
            metadata={
                "stats": stats,
                "alert_summary": alert_summary,
                "hours": hours,
            },
        )

        logger.info(
            "deployment_summary_sent",
            hours=hours,
            alert_id=alert["id"],
        )

        return {
            "status": "success",
            "alert_id": alert["id"],
            "stats": stats,
        }

    except Exception as e:
        logger.error("summary_send_failed", error=str(e))
        return {
            "status": "error",
            "message": str(e),
        }


@shared_task(bind=True, name="services.monitoring.tasks.send_deployment_summary")
def send_deployment_summary(
    self,
    hours: int = 24,
    recipients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Send deployment summary

    Args:
        hours: Number of hours to include
        recipients: Optional list of recipients

    Returns:
        Summary results
    """
    import asyncio
    return asyncio.run(_send_deployment_summary_async(hours, recipients))
