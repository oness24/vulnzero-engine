"""
Deployment Engine

Main orchestrator for patch deployment operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from shared.models import (
    Asset, Patch, Deployment, DeploymentStatus as DeploymentStatusModel,
    AuditLog, AuditAction
)
from services.deployment_orchestrator.strategies.base import (
    DeploymentStrategy, DeploymentResult, DeploymentStatus
)
from services.deployment_orchestrator.strategies.all_at_once import AllAtOnceDeployment
from services.deployment_orchestrator.strategies.rolling import RollingDeployment
from services.deployment_orchestrator.strategies.canary import CanaryDeployment
from services.deployment_orchestrator.ansible.executor import AnsibleExecutor

logger = logging.getLogger(__name__)


class DeploymentEngine:
    """
    Main orchestrator for patch deployments.

    Coordinates pre-deployment checks, strategy execution,
    post-deployment validation, and rollback.
    """

    def __init__(self, db: Session):
        """
        Initialize deployment engine.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.executor = AnsibleExecutor()

    def deploy(
        self,
        patch: Patch,
        assets: List[Asset],
        strategy: str = "all-at-once",
        strategy_params: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> DeploymentResult:
        """
        Deploy patch to assets using specified strategy.

        Args:
            patch: Patch to deploy
            assets: Target assets
            strategy: Deployment strategy name
            strategy_params: Strategy-specific parameters
            user_id: User initiating deployment

        Returns:
            DeploymentResult with outcome
        """
        self.logger.info(
            f"Starting deployment of patch {patch.id} to {len(assets)} assets "
            f"using {strategy} strategy"
        )

        # Create deployment record
        deployment = Deployment(
            patch_id=patch.id,
            strategy=strategy,
            status=DeploymentStatusModel.PENDING,
            total_assets=len(assets),
            successful_assets=0,
            failed_assets=0,
            started_at=datetime.utcnow()
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)

        # Create audit log
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.DEPLOYMENT_STARTED,
            resource_type="deployment",
            resource_id=deployment.id,
            details={
                "patch_id": patch.id,
                "asset_count": len(assets),
                "strategy": strategy
            }
        )

        try:
            # Pre-deployment checks
            validation_ok, validation_msg = self.pre_deploy_checks(patch, assets)
            if not validation_ok:
                self.logger.error(f"Pre-deployment checks failed: {validation_msg}")
                deployment.status = DeploymentStatusModel.FAILED
                deployment.error_message = f"Pre-deployment validation failed: {validation_msg}"
                deployment.completed_at = datetime.utcnow()
                self.db.commit()
                return DeploymentResult(
                    success=False,
                    message=f"Pre-deployment checks failed: {validation_msg}",
                    status=DeploymentStatus.FAILED,
                    total_assets=len(assets),
                    successful_assets=0,
                    failed_assets=len(assets)
                )

            # Update deployment status
            deployment.status = DeploymentStatusModel.IN_PROGRESS
            self.db.commit()

            # Get deployment strategy
            strategy_obj = self._get_strategy(
                strategy=strategy,
                patch=patch,
                params=strategy_params or {}
            )

            # Execute deployment
            result = strategy_obj.execute(assets)

            # Update deployment record
            deployment.successful_assets = result.successful_assets
            deployment.failed_assets = result.failed_assets
            deployment.completed_at = datetime.utcnow()

            if result.success:
                deployment.status = DeploymentStatusModel.COMPLETED
                self.logger.info(f"Deployment {deployment.id} completed successfully")
            else:
                deployment.status = DeploymentStatusModel.FAILED
                deployment.error_message = result.message
                self.logger.error(f"Deployment {deployment.id} failed: {result.message}")

            self.db.commit()

            # Post-deployment validation
            if result.success:
                validation_result = self.post_deploy_validation(patch, assets)
                if not validation_result["success"]:
                    self.logger.warning(
                        f"Post-deployment validation issues detected: "
                        f"{validation_result['issues']}"
                    )

            # Create completion audit log
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.DEPLOYMENT_COMPLETED if result.success else AuditAction.DEPLOYMENT_FAILED,
                resource_type="deployment",
                resource_id=deployment.id,
                details={
                    "success": result.success,
                    "successful_assets": result.successful_assets,
                    "failed_assets": result.failed_assets,
                    "message": result.message
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Deployment error: {e}", exc_info=True)
            deployment.status = DeploymentStatusModel.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = datetime.utcnow()
            self.db.commit()

            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.DEPLOYMENT_FAILED,
                resource_type="deployment",
                resource_id=deployment.id,
                details={"error": str(e)}
            )

            return DeploymentResult(
                success=False,
                message=f"Deployment error: {str(e)}",
                status=DeploymentStatus.FAILED,
                total_assets=len(assets),
                successful_assets=0,
                failed_assets=len(assets)
            )

    def pre_deploy_checks(
        self,
        patch: Patch,
        assets: List[Asset]
    ) -> tuple[bool, str]:
        """
        Run pre-deployment validation checks.

        Args:
            patch: Patch to deploy
            assets: Target assets

        Returns:
            (success, message) tuple
        """
        from services.deployment_orchestrator.validators.pre_deploy import PreDeployValidator

        validator = PreDeployValidator(self.db)
        return validator.validate(patch, assets)

    def post_deploy_validation(
        self,
        patch: Patch,
        assets: List[Asset]
    ) -> Dict[str, Any]:
        """
        Run post-deployment validation.

        Args:
            patch: Deployed patch
            assets: Target assets

        Returns:
            Validation results dict
        """
        from services.deployment_orchestrator.validators.post_deploy import PostDeployValidator

        validator = PostDeployValidator(self.db)
        return validator.validate(patch, assets)

    def rollback(
        self,
        deployment_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Rollback a deployment.

        Args:
            deployment_id: Deployment to rollback
            user_id: User initiating rollback

        Returns:
            True if rollback successful
        """
        self.logger.info(f"Starting rollback for deployment {deployment_id}")

        deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
        if not deployment:
            self.logger.error(f"Deployment {deployment_id} not found")
            return False

        patch = self.db.query(Patch).filter_by(id=deployment.patch_id).first()
        if not patch:
            self.logger.error(f"Patch {deployment.patch_id} not found")
            return False

        # Get assets from deployment (would need asset_deployments join table)
        # For MVP, assume we rollback all assets
        assets = self.db.query(Asset).all()

        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.DEPLOYMENT_ROLLBACK_STARTED,
            resource_type="deployment",
            resource_id=deployment_id,
            details={"patch_id": patch.id}
        )

        success_count = 0
        fail_count = 0

        for asset in assets:
            try:
                result = self.executor.execute_rollback(asset, patch)
                if result.success:
                    success_count += 1
                    self.logger.info(f"Rollback successful for asset {asset.id}")
                else:
                    fail_count += 1
                    self.logger.error(
                        f"Rollback failed for asset {asset.id}: {result.message}"
                    )
            except Exception as e:
                fail_count += 1
                self.logger.error(f"Rollback error for asset {asset.id}: {e}")

        # Update deployment status
        deployment.status = DeploymentStatusModel.ROLLED_BACK
        self.db.commit()

        overall_success = fail_count == 0

        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.DEPLOYMENT_ROLLBACK_COMPLETED,
            resource_type="deployment",
            resource_id=deployment_id,
            details={
                "success": overall_success,
                "successful_assets": success_count,
                "failed_assets": fail_count
            }
        )

        return overall_success

    def _get_strategy(
        self,
        strategy: str,
        patch: Patch,
        params: Dict[str, Any]
    ) -> DeploymentStrategy:
        """
        Get deployment strategy instance.

        Args:
            strategy: Strategy name
            patch: Patch to deploy
            params: Strategy parameters

        Returns:
            DeploymentStrategy instance
        """
        strategies = {
            "all-at-once": AllAtOnceDeployment,
            "rolling": RollingDeployment,
            "canary": CanaryDeployment,
        }

        strategy_class = strategies.get(strategy)
        if not strategy_class:
            raise ValueError(f"Unknown deployment strategy: {strategy}")

        return strategy_class(patch=patch, **params)

    def _create_audit_log(
        self,
        user_id: Optional[int],
        action: AuditAction,
        resource_type: str,
        resource_id: int,
        details: Dict[str, Any]
    ):
        """Create audit log entry"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address="internal",  # Internal system action
            user_agent="DeploymentEngine"
        )
        self.db.add(audit_log)
        self.db.commit()
