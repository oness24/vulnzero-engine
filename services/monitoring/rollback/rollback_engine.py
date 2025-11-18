"""
Rollback Engine

Automatic rollback decision-making and execution for deployments.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from services.monitoring.detectors.anomaly_detector import Anomaly, AnomalySeverity
from services.monitoring.alerts.alert_manager import AlertManager, AlertSeverity
from shared.models import Deployment, DeploymentStatus, AuditLog, AuditAction, AuditResourceType

logger = logging.getLogger(__name__)


class RollbackReason(str, Enum):
    """Reasons for rollback"""
    CRITICAL_ANOMALY = "critical_anomaly"
    MULTIPLE_HIGH_ANOMALIES = "multiple_high_anomalies"
    HIGH_ERROR_RATE = "high_error_rate"
    SERVICE_DOWNTIME = "service_downtime"
    MANUAL_TRIGGER = "manual_trigger"
    HEALTH_CHECK_FAILURE = "health_check_failure"


@dataclass
class RollbackDecision:
    """
    Represents a rollback decision.
    """
    should_rollback: bool
    reason: Optional[RollbackReason]
    confidence: float  # 0-1
    anomalies: List[Anomaly]
    message: str
    timestamp: datetime


class RollbackEngine:
    """
    Decides when to trigger automatic rollback and executes it.
    """

    def __init__(self, db: Session):
        """
        Initialize rollback engine.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

        # Rollback configuration
        self.auto_rollback_enabled = os.getenv("AUTO_ROLLBACK_ENABLED", "true").lower() == "true"
        self.critical_threshold = int(os.getenv("ROLLBACK_THRESHOLD_CRITICAL", "1"))
        self.high_threshold = int(os.getenv("ROLLBACK_THRESHOLD_HIGH", "3"))
        self.error_rate_threshold = float(os.getenv("ROLLBACK_ERROR_RATE_THRESHOLD", "10.0"))

        self.alert_manager = AlertManager(db)

    def evaluate_rollback(
        self,
        deployment_id: int,
        anomalies: List[Anomaly]
    ) -> RollbackDecision:
        """
        Evaluate if rollback should be triggered.

        Args:
            deployment_id: Deployment to evaluate
            anomalies: Detected anomalies

        Returns:
            RollbackDecision
        """
        if not self.auto_rollback_enabled:
            return RollbackDecision(
                should_rollback=False,
                reason=None,
                confidence=0.0,
                anomalies=anomalies,
                message="Automatic rollback disabled",
                timestamp=datetime.utcnow()
            )

        # Count anomalies by severity
        critical_count = sum(
            1 for a in anomalies
            if a.severity == AnomalySeverity.CRITICAL
        )
        high_count = sum(
            1 for a in anomalies
            if a.severity == AnomalySeverity.HIGH
        )

        # Decision logic
        should_rollback = False
        reason = None
        confidence = 0.0

        # Rule 1: Any critical anomaly triggers rollback
        if critical_count >= self.critical_threshold:
            should_rollback = True
            reason = RollbackReason.CRITICAL_ANOMALY
            confidence = 1.0
            message = f"Critical anomaly detected ({critical_count} critical)"

        # Rule 2: Multiple high anomalies trigger rollback
        elif high_count >= self.high_threshold:
            should_rollback = True
            reason = RollbackReason.MULTIPLE_HIGH_ANOMALIES
            confidence = 0.9
            message = f"Multiple high-severity anomalies detected ({high_count} high)"

        # Rule 3: High error rate
        else:
            error_rate_anomalies = [
                a for a in anomalies
                if "error_rate" in a.metric_name and a.metric_value > self.error_rate_threshold
            ]
            if error_rate_anomalies:
                should_rollback = True
                reason = RollbackReason.HIGH_ERROR_RATE
                confidence = 0.8
                message = f"High error rate: {error_rate_anomalies[0].metric_value:.2f}%"
            else:
                message = "No rollback conditions met"

        decision = RollbackDecision(
            should_rollback=should_rollback,
            reason=reason,
            confidence=confidence,
            anomalies=anomalies,
            message=message,
            timestamp=datetime.utcnow()
        )

        self.logger.info(
            f"Rollback decision for deployment {deployment_id}: "
            f"rollback={should_rollback}, reason={reason}, confidence={confidence:.2f}"
        )

        return decision

    def trigger_rollback(
        self,
        deployment_id: int,
        anomalies: List[Anomaly],
        user_id: Optional[int] = None,
        manual: bool = False
    ) -> bool:
        """
        Trigger rollback for a deployment.

        Args:
            deployment_id: Deployment to rollback
            anomalies: Anomalies that triggered rollback
            user_id: User triggering rollback (if manual)
            manual: True if manually triggered

        Returns:
            True if rollback successful
        """
        self.logger.warning(
            f"Triggering rollback for deployment {deployment_id} "
            f"({'manual' if manual else 'automatic'})"
        )

        # Get deployment
        deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
        if not deployment:
            self.logger.error(f"Deployment {deployment_id} not found")
            return False

        # Check if already rolled back
        if deployment.status == DeploymentStatus.ROLLED_BACK:
            self.logger.warning(f"Deployment {deployment_id} already rolled back")
            return False

        try:
            # Create critical alert
            for anomaly in anomalies:
                alert = self.alert_manager.create_alert_from_anomaly(
                    anomaly=anomaly,
                    deployment_id=deployment_id
                )
                self.alert_manager.send_alert(alert, channels=["slack", "email"])

            # Execute rollback via deployment orchestrator
            from services.deployment_orchestrator.core.engine import DeploymentEngine

            engine = DeploymentEngine(self.db)
            success = engine.rollback(
                deployment_id=deployment_id,
                user_id=user_id
            )

            if success:
                self.logger.info(f"Rollback successful for deployment {deployment_id}")

                # Create audit log
                audit_log = AuditLog(
                    action=AuditAction.DEPLOYMENT_ROLLBACK_COMPLETED,
                    timestamp=datetime.utcnow(),
                    actor_type="system" if not manual else "user",
                    actor_id=user_id or "rollback_engine",
                    actor_name="RollbackEngine",
                    actor_ip="internal",
                    actor_user_agent="RollbackEngine",
                    resource_type=AuditResourceType.DEPLOYMENT,
                    resource_id=str(deployment_id),
                    description=f"Rollback completed for deployment {deployment_id} ({'manual' if manual else 'automatic'})",
                    success=1,
                    details={
                        "trigger": "manual" if manual else "automatic",
                        "anomaly_count": len(anomalies),
                        "anomalies": [
                            {
                                "type": a.anomaly_type.value,
                                "severity": a.severity.value,
                                "metric": a.metric_name,
                                "value": a.metric_value
                            }
                            for a in anomalies
                        ]
                    }
                )
                self.db.add(audit_log)
                self.db.commit()

            else:
                self.logger.error(f"Rollback failed for deployment {deployment_id}")

                # Create failure audit log
                audit_log = AuditLog(
                    action=AuditAction.DEPLOYMENT_ROLLBACK_FAILED,
                    timestamp=datetime.utcnow(),
                    actor_type="system" if not manual else "user",
                    actor_id=user_id or "rollback_engine",
                    actor_name="RollbackEngine",
                    actor_ip="internal",
                    actor_user_agent="RollbackEngine",
                    resource_type=AuditResourceType.DEPLOYMENT,
                    resource_id=str(deployment_id),
                    description=f"Rollback failed for deployment {deployment_id}",
                    success=0,
                    error_message="Rollback execution failed",
                    details={"error": "Rollback execution failed"}
                )
                self.db.add(audit_log)
                self.db.commit()

            return success

        except Exception as e:
            self.logger.error(
                f"Error during rollback of deployment {deployment_id}: {e}",
                exc_info=True
            )

            # Create error audit log
            audit_log = AuditLog(
                action=AuditAction.DEPLOYMENT_ROLLBACK_FAILED,
                timestamp=datetime.utcnow(),
                actor_type="system" if not manual else "user",
                actor_id=user_id or "rollback_engine",
                actor_name="RollbackEngine",
                actor_ip="internal",
                actor_user_agent="RollbackEngine",
                resource_type=AuditResourceType.DEPLOYMENT,
                resource_id=str(deployment_id),
                description=f"Rollback error for deployment {deployment_id}",
                success=0,
                error_message=str(e),
                details={"error": str(e)}
            )
            self.db.add(audit_log)
            self.db.commit()

            return False

    def get_rollback_eligibility(self, deployment_id: int) -> Dict[str, Any]:
        """
        Check if deployment is eligible for rollback.

        Args:
            deployment_id: Deployment to check

        Returns:
            Dict with eligibility status and reason
        """
        deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
        if not deployment:
            return {
                "eligible": False,
                "reason": "Deployment not found"
            }

        # Check deployment status
        if deployment.status == DeploymentStatus.ROLLED_BACK:
            return {
                "eligible": False,
                "reason": "Already rolled back"
            }

        if deployment.status == DeploymentStatus.PENDING:
            return {
                "eligible": False,
                "reason": "Deployment not started"
            }

        # Check if patch has rollback script
        from shared.models import Patch
        patch = self.db.query(Patch).filter_by(id=deployment.patch_id).first()
        if not patch or not patch.rollback_script:
            return {
                "eligible": False,
                "reason": "No rollback script available"
            }

        return {
            "eligible": True,
            "reason": "Eligible for rollback"
        }
