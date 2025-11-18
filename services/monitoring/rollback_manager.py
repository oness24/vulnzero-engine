"""
Automatic rollback management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class RollbackManager:
    """
    Manages automatic rollbacks based on deployment health
    """

    def __init__(self):
        self.rollback_history = []
        self.rollback_rules = []

    def should_rollback(
        self,
        deployment_id: int,
        monitoring_data: Dict[str, Any],
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Determine if deployment should be rolled back

        Args:
            deployment_id: Deployment ID
            monitoring_data: Monitoring data from deployment
            rules: Optional custom rollback rules

        Returns:
            Dictionary with rollback decision and reasons
        """
        logger.info("evaluating_rollback", deployment_id=deployment_id)

        decision = {
            "should_rollback": False,
            "reasons": [],
            "severity": "none",
            "confidence": 0.0,
        }

        # Use custom rules or default rules
        rules_to_check = rules or self._get_default_rules()

        for rule in rules_to_check:
            rule_result = self._evaluate_rule(rule, monitoring_data)

            if rule_result["triggered"]:
                decision["should_rollback"] = True
                decision["reasons"].append({
                    "rule": rule["name"],
                    "description": rule["description"],
                    "severity": rule.get("severity", "medium"),
                    "details": rule_result.get("details", {}),
                })

                # Update overall severity
                if self._get_severity_level(rule.get("severity", "medium")) > self._get_severity_level(decision["severity"]):
                    decision["severity"] = rule.get("severity", "medium")

        # Calculate confidence based on number of triggered rules
        if decision["should_rollback"]:
            decision["confidence"] = min(1.0, len(decision["reasons"]) * 0.25)

        logger.info(
            "rollback_evaluation_complete",
            deployment_id=deployment_id,
            should_rollback=decision["should_rollback"],
            reasons_count=len(decision["reasons"]),
        )

        return decision

    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """Get default rollback rules"""
        return [
            {
                "name": "consecutive_health_check_failures",
                "description": "Multiple consecutive health check failures",
                "type": "health_check",
                "threshold": 3,
                "severity": "high",
            },
            {
                "name": "high_failure_rate",
                "description": "More than 50% of assets failing",
                "type": "failure_rate",
                "threshold": 0.5,
                "severity": "critical",
            },
            {
                "name": "critical_service_down",
                "description": "Critical service is not responding",
                "type": "service_health",
                "severity": "critical",
            },
            {
                "name": "error_rate_spike",
                "description": "Error rate increased significantly",
                "type": "error_rate",
                "threshold": 2.0,  # 2x increase
                "severity": "high",
            },
            {
                "name": "resource_exhaustion",
                "description": "Resource usage exceeded threshold",
                "type": "resource",
                "threshold": 90.0,  # 90% usage
                "severity": "medium",
            },
        ]

    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate a single rollback rule

        Args:
            rule: Rule to evaluate
            monitoring_data: Monitoring data

        Returns:
            Evaluation result
        """
        rule_type = rule.get("type")

        if rule_type == "health_check":
            return self._evaluate_health_check_rule(rule, monitoring_data)
        elif rule_type == "failure_rate":
            return self._evaluate_failure_rate_rule(rule, monitoring_data)
        elif rule_type == "service_health":
            return self._evaluate_service_health_rule(rule, monitoring_data)
        elif rule_type == "error_rate":
            return self._evaluate_error_rate_rule(rule, monitoring_data)
        elif rule_type == "resource":
            return self._evaluate_resource_rule(rule, monitoring_data)
        else:
            return {"triggered": False}

    def _evaluate_health_check_rule(
        self,
        rule: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate consecutive health check failures"""
        health_checks = monitoring_data.get("health_checks", [])
        threshold = rule.get("threshold", 3)

        if len(health_checks) < threshold:
            return {"triggered": False}

        # Check last N health checks
        recent_checks = health_checks[-threshold:]
        all_failed = all(not check.get("all_healthy", True) for check in recent_checks)

        if all_failed:
            return {
                "triggered": True,
                "details": {
                    "consecutive_failures": threshold,
                    "last_check": recent_checks[-1],
                },
            }

        return {"triggered": False}

    def _evaluate_failure_rate_rule(
        self,
        rule: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate failure rate threshold"""
        health_checks = monitoring_data.get("health_checks", [])

        if not health_checks:
            return {"triggered": False}

        latest_check = health_checks[-1]
        total = latest_check.get("total_assets", 0)
        failed = latest_check.get("failed_count", 0)

        if total == 0:
            return {"triggered": False}

        failure_rate = failed / total
        threshold = rule.get("threshold", 0.5)

        if failure_rate > threshold:
            return {
                "triggered": True,
                "details": {
                    "failure_rate": failure_rate,
                    "threshold": threshold,
                    "failed_assets": failed,
                    "total_assets": total,
                },
            }

        return {"triggered": False}

    def _evaluate_service_health_rule(
        self,
        rule: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate critical service health"""
        # This would check if critical services are responding
        # For now, simplified implementation
        health_checks = monitoring_data.get("health_checks", [])

        if not health_checks:
            return {"triggered": False}

        latest_check = health_checks[-1]
        failed_assets = latest_check.get("failed_assets", [])

        # If any asset has service-related failures, trigger
        service_failures = [
            asset for asset in failed_assets
            if "service" in asset.get("reason", "").lower()
        ]

        if service_failures:
            return {
                "triggered": True,
                "details": {
                    "failed_services": service_failures,
                },
            }

        return {"triggered": False}

    def _evaluate_error_rate_rule(
        self,
        rule: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate error rate increase"""
        # Would compare current error rate to baseline
        # Simplified for now
        alerts = monitoring_data.get("alerts", [])

        # If there are multiple error alerts, trigger
        error_alerts = [
            alert for alert in alerts
            if alert.get("severity") in ["error", "critical"]
        ]

        threshold = rule.get("threshold", 2.0)

        if len(error_alerts) >= threshold:
            return {
                "triggered": True,
                "details": {
                    "error_count": len(error_alerts),
                    "threshold": threshold,
                },
            }

        return {"triggered": False}

    def _evaluate_resource_rule(
        self,
        rule: Dict[str, Any],
        monitoring_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate resource usage thresholds"""
        metrics = monitoring_data.get("metrics", [])

        if not metrics:
            return {"triggered": False}

        # Get latest metrics
        latest_metrics = metrics[-1] if metrics else {}
        asset_metrics = latest_metrics.get("asset_metrics", [])

        threshold = rule.get("threshold", 90.0)
        overloaded_assets = []

        for asset_metric in asset_metrics:
            metrics_data = asset_metric.get("metrics", {})

            # Check CPU, memory, disk usage
            for metric_name in ["cpu_usage", "memory_usage", "disk_usage"]:
                usage = metrics_data.get(metric_name, 0.0)
                if usage > threshold:
                    overloaded_assets.append({
                        "asset": asset_metric.get("asset"),
                        "metric": metric_name,
                        "usage": usage,
                    })

        if overloaded_assets:
            return {
                "triggered": True,
                "details": {
                    "overloaded_assets": overloaded_assets,
                    "threshold": threshold,
                },
            }

        return {"triggered": False}

    def _get_severity_level(self, severity: str) -> int:
        """Convert severity to numeric level"""
        severity_levels = {
            "none": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }
        return severity_levels.get(severity, 0)

    async def execute_automatic_rollback(
        self,
        deployment_id: int,
        reason: str,
        rollback_func: callable,
    ) -> Dict[str, Any]:
        """
        Execute automatic rollback

        Args:
            deployment_id: Deployment ID to rollback
            reason: Reason for rollback
            rollback_func: Function to execute rollback

        Returns:
            Rollback execution results
        """
        logger.info(
            "executing_automatic_rollback",
            deployment_id=deployment_id,
            reason=reason,
        )

        rollback_record = {
            "deployment_id": deployment_id,
            "started_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "automatic": True,
        }

        try:
            # Execute rollback
            result = await rollback_func(deployment_id)

            rollback_record["completed_at"] = datetime.utcnow().isoformat()
            rollback_record["success"] = result.get("success", False)
            rollback_record["result"] = result

            self.rollback_history.append(rollback_record)

            logger.info(
                "automatic_rollback_completed",
                deployment_id=deployment_id,
                success=rollback_record["success"],
            )

            return rollback_record

        except Exception as e:
            logger.error(
                "automatic_rollback_failed",
                deployment_id=deployment_id,
                error=str(e),
            )

            rollback_record["completed_at"] = datetime.utcnow().isoformat()
            rollback_record["success"] = False
            rollback_record["error"] = str(e)

            self.rollback_history.append(rollback_record)

            return rollback_record

    def get_rollback_history(
        self,
        deployment_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get rollback history

        Args:
            deployment_id: Optional filter by deployment ID
            limit: Maximum number of records to return

        Returns:
            List of rollback records
        """
        if deployment_id:
            history = [
                record for record in self.rollback_history
                if record["deployment_id"] == deployment_id
            ]
        else:
            history = self.rollback_history

        return history[-limit:]

    def add_custom_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Add a custom rollback rule

        Args:
            rule: Rollback rule definition

        Returns:
            True if added successfully
        """
        required_fields = ["name", "description", "type"]

        if not all(field in rule for field in required_fields):
            logger.error("invalid_rule", rule=rule)
            return False

        self.rollback_rules.append(rule)

        logger.info("custom_rule_added", rule_name=rule["name"])
        return True

    def remove_custom_rule(self, rule_name: str) -> bool:
        """
        Remove a custom rollback rule

        Args:
            rule_name: Name of rule to remove

        Returns:
            True if removed
        """
        initial_count = len(self.rollback_rules)
        self.rollback_rules = [
            rule for rule in self.rollback_rules
            if rule["name"] != rule_name
        ]

        removed = len(self.rollback_rules) < initial_count

        if removed:
            logger.info("custom_rule_removed", rule_name=rule_name)

        return removed
