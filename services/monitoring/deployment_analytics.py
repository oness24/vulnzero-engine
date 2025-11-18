"""
Deployment analytics and tracking
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class DeploymentAnalytics:
    """
    Tracks and analyzes deployment metrics and history
    """

    def __init__(self):
        self.deployment_history = []
        self.metrics_cache = {}

    async def track_deployment_start(
        self,
        deployment_id: int,
        patch_id: int,
        strategy: str,
        asset_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Track deployment start

        Args:
            deployment_id: Deployment ID
            patch_id: Patch ID
            strategy: Deployment strategy
            asset_count: Number of assets
            metadata: Optional metadata

        Returns:
            Tracking record
        """
        record = {
            "deployment_id": deployment_id,
            "patch_id": patch_id,
            "strategy": strategy,
            "asset_count": asset_count,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "metadata": metadata or {},
        }

        self.deployment_history.append(record)

        logger.info(
            "deployment_tracking_started",
            deployment_id=deployment_id,
            strategy=strategy,
            asset_count=asset_count,
        )

        return record

    async def track_deployment_completion(
        self,
        deployment_id: int,
        success: bool,
        results: Dict[str, Any],
        duration: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Track deployment completion

        Args:
            deployment_id: Deployment ID
            success: Whether deployment succeeded
            results: Deployment results
            duration: Deployment duration in seconds

        Returns:
            Updated tracking record
        """
        # Find and update record
        record = None
        for r in self.deployment_history:
            if r["deployment_id"] == deployment_id:
                record = r
                break

        if not record:
            logger.warning(
                "deployment_record_not_found",
                deployment_id=deployment_id,
            )
            return {}

        record["completed_at"] = datetime.utcnow().isoformat()
        record["status"] = "completed" if success else "failed"
        record["success"] = success
        record["results"] = results

        if duration:
            record["duration_seconds"] = duration
        elif "started_at" in record:
            started = datetime.fromisoformat(record["started_at"])
            completed = datetime.fromisoformat(record["completed_at"])
            record["duration_seconds"] = (completed - started).total_seconds()

        logger.info(
            "deployment_tracking_completed",
            deployment_id=deployment_id,
            success=success,
            duration=record.get("duration_seconds"),
        )

        # Clear cache to force recalculation
        self.metrics_cache = {}

        return record

    async def track_rollback(
        self,
        deployment_id: int,
        rollback_id: int,
        reason: str,
        success: bool,
        results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Track deployment rollback

        Args:
            deployment_id: Deployment ID
            rollback_id: Rollback ID
            reason: Rollback reason
            success: Whether rollback succeeded
            results: Rollback results

        Returns:
            Rollback tracking record
        """
        record = {
            "rollback_id": rollback_id,
            "deployment_id": deployment_id,
            "reason": reason,
            "success": success,
            "results": results or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Update deployment record
        for r in self.deployment_history:
            if r["deployment_id"] == deployment_id:
                r["rolled_back"] = True
                r["rollback_record"] = record
                break

        logger.info(
            "rollback_tracked",
            deployment_id=deployment_id,
            rollback_id=rollback_id,
            success=success,
        )

        # Clear cache
        self.metrics_cache = {}

        return record

    async def get_deployment_stats(
        self,
        hours: int = 24,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get deployment statistics

        Args:
            hours: Number of hours to analyze
            strategy: Optional filter by strategy

        Returns:
            Deployment statistics
        """
        cache_key = f"stats_{hours}_{strategy}"
        if cache_key in self.metrics_cache:
            return self.metrics_cache[cache_key]

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Filter deployments
        deployments = [
            d for d in self.deployment_history
            if datetime.fromisoformat(d["started_at"]) > cutoff
        ]

        if strategy:
            deployments = [d for d in deployments if d.get("strategy") == strategy]

        # Calculate stats
        total = len(deployments)
        completed = [d for d in deployments if d.get("status") == "completed"]
        failed = [d for d in deployments if d.get("status") == "failed"]
        in_progress = [d for d in deployments if d.get("status") == "in_progress"]
        rolled_back = [d for d in deployments if d.get("rolled_back", False)]

        stats = {
            "total_deployments": total,
            "completed": len(completed),
            "failed": len(failed),
            "in_progress": len(in_progress),
            "rolled_back": len(rolled_back),
            "success_rate": (len(completed) / total * 100) if total > 0 else 0,
            "failure_rate": (len(failed) / total * 100) if total > 0 else 0,
            "rollback_rate": (len(rolled_back) / total * 100) if total > 0 else 0,
            "by_strategy": self._get_strategy_breakdown(deployments),
            "average_duration": self._get_average_duration(completed),
            "time_period_hours": hours,
        }

        self.metrics_cache[cache_key] = stats
        return stats

    def _get_strategy_breakdown(
        self,
        deployments: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get breakdown by deployment strategy

        Args:
            deployments: List of deployments

        Returns:
            Strategy breakdown
        """
        breakdown = defaultdict(lambda: {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "rolled_back": 0,
        })

        for d in deployments:
            strategy = d.get("strategy", "unknown")
            breakdown[strategy]["total"] += 1

            if d.get("status") == "completed":
                breakdown[strategy]["completed"] += 1
            elif d.get("status") == "failed":
                breakdown[strategy]["failed"] += 1

            if d.get("rolled_back", False):
                breakdown[strategy]["rolled_back"] += 1

        # Calculate success rates
        for strategy, stats in breakdown.items():
            total = stats["total"]
            if total > 0:
                stats["success_rate"] = (stats["completed"] / total * 100)
                stats["failure_rate"] = (stats["failed"] / total * 100)
                stats["rollback_rate"] = (stats["rolled_back"] / total * 100)

        return dict(breakdown)

    def _get_average_duration(self, deployments: List[Dict[str, Any]]) -> Optional[float]:
        """
        Calculate average deployment duration

        Args:
            deployments: List of completed deployments

        Returns:
            Average duration in seconds or None
        """
        durations = [
            d["duration_seconds"] for d in deployments
            if "duration_seconds" in d
        ]

        if not durations:
            return None

        return sum(durations) / len(durations)

    async def get_asset_deployment_history(
        self,
        asset_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get deployment history for specific asset

        Args:
            asset_id: Asset ID
            limit: Maximum number of records

        Returns:
            List of deployment records
        """
        # Note: This would need asset tracking in deployment records
        # For now, return placeholder
        history = []

        for deployment in reversed(self.deployment_history[-limit:]):
            if "assets" in deployment.get("results", {}):
                # Check if asset was part of deployment
                asset_results = deployment["results"].get("assets", [])
                for asset_result in asset_results:
                    if asset_result.get("asset_id") == asset_id:
                        history.append({
                            "deployment_id": deployment["deployment_id"],
                            "patch_id": deployment["patch_id"],
                            "strategy": deployment["strategy"],
                            "started_at": deployment["started_at"],
                            "status": deployment["status"],
                            "asset_status": asset_result.get("status"),
                            "asset_result": asset_result,
                        })
                        break

        return history[:limit]

    async def get_patch_deployment_stats(
        self,
        patch_id: int,
    ) -> Dict[str, Any]:
        """
        Get deployment statistics for specific patch

        Args:
            patch_id: Patch ID

        Returns:
            Patch deployment statistics
        """
        deployments = [
            d for d in self.deployment_history
            if d.get("patch_id") == patch_id
        ]

        total_assets = 0
        successful_assets = 0
        failed_assets = 0

        for d in deployments:
            if "results" in d:
                total_assets += d["results"].get("total_assets", 0)
                successful_assets += d["results"].get("successful", 0)
                failed_assets += d["results"].get("failed", 0)

        stats = {
            "patch_id": patch_id,
            "total_deployments": len(deployments),
            "total_assets": total_assets,
            "successful_assets": successful_assets,
            "failed_assets": failed_assets,
            "success_rate": (
                (successful_assets / total_assets * 100)
                if total_assets > 0 else 0
            ),
            "deployments": [
                {
                    "deployment_id": d["deployment_id"],
                    "strategy": d["strategy"],
                    "started_at": d["started_at"],
                    "status": d.get("status"),
                    "rolled_back": d.get("rolled_back", False),
                }
                for d in deployments
            ],
        }

        return stats

    async def get_failure_analysis(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Analyze deployment failures

        Args:
            hours: Number of hours to analyze

        Returns:
            Failure analysis
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        failed_deployments = [
            d for d in self.deployment_history
            if d.get("status") == "failed"
            and datetime.fromisoformat(d["started_at"]) > cutoff
        ]

        # Categorize failures
        failure_reasons = defaultdict(int)
        failure_by_strategy = defaultdict(int)
        failure_by_patch = defaultdict(int)

        for d in failed_deployments:
            strategy = d.get("strategy", "unknown")
            patch_id = d.get("patch_id", "unknown")

            failure_by_strategy[strategy] += 1
            failure_by_patch[patch_id] += 1

            # Extract failure reason from results
            results = d.get("results", {})
            if "error" in results:
                failure_reasons["execution_error"] += 1
            elif "failed" in results and results.get("failed", 0) > 0:
                failure_reasons["asset_failure"] += 1
            else:
                failure_reasons["unknown"] += 1

        analysis = {
            "total_failures": len(failed_deployments),
            "failure_reasons": dict(failure_reasons),
            "failure_by_strategy": dict(failure_by_strategy),
            "failure_by_patch": dict(failure_by_patch),
            "time_period_hours": hours,
            "recent_failures": [
                {
                    "deployment_id": d["deployment_id"],
                    "patch_id": d["patch_id"],
                    "strategy": d["strategy"],
                    "started_at": d["started_at"],
                    "error": d.get("results", {}).get("error", "Unknown"),
                }
                for d in failed_deployments[-5:]  # Last 5 failures
            ],
        }

        return analysis

    async def get_performance_metrics(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get deployment performance metrics

        Args:
            hours: Number of hours to analyze

        Returns:
            Performance metrics
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        completed_deployments = [
            d for d in self.deployment_history
            if d.get("status") == "completed"
            and datetime.fromisoformat(d["started_at"]) > cutoff
            and "duration_seconds" in d
        ]

        if not completed_deployments:
            return {
                "total_deployments": 0,
                "metrics": {},
            }

        durations = [d["duration_seconds"] for d in completed_deployments]
        asset_counts = [d.get("asset_count", 0) for d in completed_deployments]

        metrics = {
            "total_deployments": len(completed_deployments),
            "average_duration_seconds": sum(durations) / len(durations),
            "min_duration_seconds": min(durations),
            "max_duration_seconds": max(durations),
            "average_assets_per_deployment": (
                sum(asset_counts) / len(asset_counts)
                if asset_counts else 0
            ),
            "total_assets_deployed": sum(asset_counts),
            "time_period_hours": hours,
            "by_strategy": self._get_performance_by_strategy(completed_deployments),
        }

        return metrics

    def _get_performance_by_strategy(
        self,
        deployments: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics by strategy

        Args:
            deployments: List of completed deployments

        Returns:
            Performance by strategy
        """
        by_strategy = defaultdict(list)

        for d in deployments:
            strategy = d.get("strategy", "unknown")
            if "duration_seconds" in d:
                by_strategy[strategy].append(d["duration_seconds"])

        metrics = {}
        for strategy, durations in by_strategy.items():
            if durations:
                metrics[strategy] = {
                    "count": len(durations),
                    "average_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }

        return metrics

    async def export_deployment_history(
        self,
        hours: Optional[int] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Export deployment history

        Args:
            hours: Optional number of hours (None = all history)
            format: Export format (json, csv)

        Returns:
            Exported data
        """
        deployments = self.deployment_history

        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            deployments = [
                d for d in deployments
                if datetime.fromisoformat(d["started_at"]) > cutoff
            ]

        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_records": len(deployments),
            "time_period_hours": hours,
            "format": format,
            "deployments": deployments,
        }

        logger.info(
            "deployment_history_exported",
            records=len(deployments),
            format=format,
        )

        return export_data

    async def clear_old_history(self, days: int = 30) -> int:
        """
        Clear deployment history older than specified days

        Args:
            days: Number of days to keep

        Returns:
            Number of records cleared
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        initial_count = len(self.deployment_history)

        self.deployment_history = [
            d for d in self.deployment_history
            if datetime.fromisoformat(d["started_at"]) > cutoff
        ]

        cleared = initial_count - len(self.deployment_history)

        logger.info(
            "deployment_history_cleared",
            cleared=cleared,
            remaining=len(self.deployment_history),
            days=days,
        )

        # Clear cache
        self.metrics_cache = {}

        return cleared
