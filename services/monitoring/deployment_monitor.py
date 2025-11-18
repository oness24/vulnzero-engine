"""
Real-time deployment monitoring
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import asyncio
import structlog

logger = structlog.get_logger()


class DeploymentMonitor:
    """
    Monitors deployments in real-time and tracks health metrics
    """

    def __init__(self):
        self.active_monitors = {}
        self.health_checks = []

    async def monitor_deployment(
        self,
        deployment_id: int,
        assets: List[Dict[str, Any]],
        check_interval: int = 30,
        max_duration: int = 3600,
        health_check_func: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Monitor a deployment in real-time

        Args:
            deployment_id: Deployment ID to monitor
            assets: List of assets being deployed to
            check_interval: Interval between health checks (seconds)
            max_duration: Maximum monitoring duration (seconds)
            health_check_func: Optional custom health check function

        Returns:
            Monitoring results
        """
        logger.info(
            "starting_deployment_monitoring",
            deployment_id=deployment_id,
            asset_count=len(assets),
        )

        monitoring_result = {
            "deployment_id": deployment_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "monitoring",
            "health_checks": [],
            "alerts": [],
            "should_rollback": False,
        }

        self.active_monitors[deployment_id] = monitoring_result

        start_time = datetime.utcnow()
        check_count = 0

        try:
            while True:
                # Check if max duration exceeded
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > max_duration:
                    logger.warning(
                        "monitoring_duration_exceeded",
                        deployment_id=deployment_id,
                    )
                    break

                # Perform health checks
                check_count += 1
                health_result = await self._perform_health_checks(
                    assets,
                    health_check_func,
                )

                health_result["check_number"] = check_count
                health_result["timestamp"] = datetime.utcnow().isoformat()
                monitoring_result["health_checks"].append(health_result)

                # Analyze health results
                if not health_result["all_healthy"]:
                    alert = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "severity": "warning",
                        "message": f"Health check failed for {health_result['failed_count']} assets",
                        "failed_assets": health_result["failed_assets"],
                    }
                    monitoring_result["alerts"].append(alert)

                    # Check if rollback is needed
                    if self._should_trigger_rollback(monitoring_result):
                        logger.error(
                            "rollback_triggered",
                            deployment_id=deployment_id,
                        )
                        monitoring_result["should_rollback"] = True
                        monitoring_result["status"] = "rollback_required"
                        break

                # Wait before next check
                await asyncio.sleep(check_interval)

        except Exception as e:
            logger.error(
                "monitoring_error",
                deployment_id=deployment_id,
                error=str(e),
            )
            monitoring_result["error"] = str(e)
            monitoring_result["status"] = "error"

        monitoring_result["completed_at"] = datetime.utcnow().isoformat()
        monitoring_result["total_checks"] = check_count

        # Remove from active monitors
        if deployment_id in self.active_monitors:
            del self.active_monitors[deployment_id]

        logger.info(
            "deployment_monitoring_completed",
            deployment_id=deployment_id,
            total_checks=check_count,
            should_rollback=monitoring_result["should_rollback"],
        )

        return monitoring_result

    async def _perform_health_checks(
        self,
        assets: List[Dict[str, Any]],
        health_check_func: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Perform health checks on all assets

        Args:
            assets: List of assets to check
            health_check_func: Optional custom health check function

        Returns:
            Health check results
        """
        if health_check_func:
            # Use custom health check
            tasks = [health_check_func(asset) for asset in assets]
        else:
            # Use default health check
            tasks = [self._default_health_check(asset) for asset in assets]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy_count = 0
        failed_count = 0
        failed_assets = []

        for asset, result in zip(assets, results):
            if isinstance(result, Exception):
                failed_count += 1
                failed_assets.append({
                    "asset": asset.get("name"),
                    "error": str(result),
                })
            elif result.get("healthy", False):
                healthy_count += 1
            else:
                failed_count += 1
                failed_assets.append({
                    "asset": asset.get("name"),
                    "reason": result.get("reason", "Unknown"),
                })

        return {
            "total_assets": len(assets),
            "healthy_count": healthy_count,
            "failed_count": failed_count,
            "all_healthy": failed_count == 0,
            "failed_assets": failed_assets,
        }

    async def _default_health_check(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default health check for an asset

        Args:
            asset: Asset to check

        Returns:
            Health check result
        """
        from services.deployment_engine.connection_manager import get_connection_manager

        conn_manager = get_connection_manager("ssh")

        try:
            # Try to connect
            if not conn_manager.connect(asset, timeout=10):
                return {
                    "healthy": False,
                    "reason": "Connection failed",
                }

            # Execute simple health check command
            result = conn_manager.execute_command(
                "echo 'healthy' && exit 0",
                timeout=10,
            )

            conn_manager.disconnect()

            if result["success"]:
                return {
                    "healthy": True,
                    "response_time_ms": 100,  # Could measure actual time
                }
            else:
                return {
                    "healthy": False,
                    "reason": "Health check command failed",
                }

        except Exception as e:
            return {
                "healthy": False,
                "reason": str(e),
            }

    def _should_trigger_rollback(
        self,
        monitoring_result: Dict[str, Any],
    ) -> bool:
        """
        Determine if rollback should be triggered

        Args:
            monitoring_result: Current monitoring results

        Returns:
            True if rollback should be triggered
        """
        health_checks = monitoring_result.get("health_checks", [])

        if len(health_checks) < 3:
            # Need at least 3 checks before triggering rollback
            return False

        # Get last 3 checks
        recent_checks = health_checks[-3:]

        # If all 3 recent checks show failures, trigger rollback
        all_failed = all(not check.get("all_healthy", True) for check in recent_checks)

        if all_failed:
            return True

        # If more than 50% of assets are failing, trigger rollback
        latest_check = health_checks[-1]
        total = latest_check.get("total_assets", 0)
        failed = latest_check.get("failed_count", 0)

        if total > 0 and (failed / total) > 0.5:
            return True

        return False

    def get_monitoring_status(self, deployment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current monitoring status for a deployment

        Args:
            deployment_id: Deployment ID

        Returns:
            Current monitoring status or None
        """
        return self.active_monitors.get(deployment_id)

    def stop_monitoring(self, deployment_id: int) -> bool:
        """
        Stop monitoring a deployment

        Args:
            deployment_id: Deployment ID

        Returns:
            True if monitoring was stopped
        """
        if deployment_id in self.active_monitors:
            del self.active_monitors[deployment_id]
            logger.info("monitoring_stopped", deployment_id=deployment_id)
            return True
        return False

    async def monitor_deployment_with_metrics(
        self,
        deployment_id: int,
        assets: List[Dict[str, Any]],
        metrics_to_collect: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Monitor deployment and collect detailed metrics

        Args:
            deployment_id: Deployment ID
            assets: Assets to monitor
            metrics_to_collect: List of metrics to collect (cpu, memory, disk, network)

        Returns:
            Monitoring results with metrics
        """
        metrics_to_collect = metrics_to_collect or ["cpu", "memory", "disk"]

        logger.info(
            "starting_metrics_monitoring",
            deployment_id=deployment_id,
            metrics=metrics_to_collect,
        )

        result = {
            "deployment_id": deployment_id,
            "started_at": datetime.utcnow().isoformat(),
            "metrics": [],
        }

        # Collect baseline metrics
        baseline = await self._collect_metrics(assets, metrics_to_collect)
        baseline["timestamp"] = datetime.utcnow().isoformat()
        baseline["type"] = "baseline"
        result["metrics"].append(baseline)

        # Monitor for changes (simplified - would be more sophisticated in production)
        await asyncio.sleep(60)  # Wait 1 minute

        # Collect post-deployment metrics
        post_deployment = await self._collect_metrics(assets, metrics_to_collect)
        post_deployment["timestamp"] = datetime.utcnow().isoformat()
        post_deployment["type"] = "post_deployment"
        result["metrics"].append(post_deployment)

        result["completed_at"] = datetime.utcnow().isoformat()

        logger.info("metrics_monitoring_completed", deployment_id=deployment_id)

        return result

    async def _collect_metrics(
        self,
        assets: List[Dict[str, Any]],
        metrics: List[str],
    ) -> Dict[str, Any]:
        """
        Collect metrics from assets

        Args:
            assets: Assets to collect from
            metrics: Metrics to collect

        Returns:
            Collected metrics
        """
        from services.deployment_engine.connection_manager import get_connection_manager

        metrics_data = {
            "asset_metrics": [],
        }

        for asset in assets:
            asset_metrics = {
                "asset": asset.get("name"),
                "metrics": {},
            }

            conn_manager = get_connection_manager("ssh")

            try:
                if not conn_manager.connect(asset, timeout=10):
                    asset_metrics["error"] = "Connection failed"
                    metrics_data["asset_metrics"].append(asset_metrics)
                    continue

                # Collect CPU usage
                if "cpu" in metrics:
                    cpu_result = conn_manager.execute_command(
                        "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'",
                        timeout=10,
                    )
                    if cpu_result["success"]:
                        try:
                            asset_metrics["metrics"]["cpu_usage"] = float(cpu_result["stdout"].strip())
                        except:
                            asset_metrics["metrics"]["cpu_usage"] = 0.0

                # Collect memory usage
                if "memory" in metrics:
                    mem_result = conn_manager.execute_command(
                        "free | grep Mem | awk '{print ($3/$2) * 100.0}'",
                        timeout=10,
                    )
                    if mem_result["success"]:
                        try:
                            asset_metrics["metrics"]["memory_usage"] = float(mem_result["stdout"].strip())
                        except:
                            asset_metrics["metrics"]["memory_usage"] = 0.0

                # Collect disk usage
                if "disk" in metrics:
                    disk_result = conn_manager.execute_command(
                        "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'",
                        timeout=10,
                    )
                    if disk_result["success"]:
                        try:
                            asset_metrics["metrics"]["disk_usage"] = float(disk_result["stdout"].strip())
                        except:
                            asset_metrics["metrics"]["disk_usage"] = 0.0

                conn_manager.disconnect()

            except Exception as e:
                asset_metrics["error"] = str(e)

            metrics_data["asset_metrics"].append(asset_metrics)

        return metrics_data
