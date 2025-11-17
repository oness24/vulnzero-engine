"""
Deployment Celery Tasks

Async tasks for patch deployment orchestration.
"""

import logging
from typing import List, Dict, Any, Optional
from celery import Task
from sqlalchemy.orm import Session

from services.deployment_orchestrator.tasks.celery_app import celery_app
from services.deployment_orchestrator.core.engine import DeploymentEngine
from shared.database import get_db
from shared.models import (
    Patch, Asset, Deployment, DeploymentStatus,
    AuditLog, AuditAction
)

logger = logging.getLogger(__name__)


class DeploymentTask(Task):
    """Base task with database session management"""

    def __call__(self, *args, **kwargs):
        """Execute task with database session"""
        db = next(get_db())
        try:
            return self.run(*args, db=db, **kwargs)
        finally:
            db.close()


@celery_app.task(
    bind=True,
    base=DeploymentTask,
    name="deployment_orchestrator.deploy_patch",
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def deploy_patch(
    self,
    patch_id: int,
    asset_ids: List[int],
    strategy: str = "all-at-once",
    strategy_params: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    db: Session = None
):
    """
    Deploy patch to assets asynchronously.

    Args:
        patch_id: Patch to deploy
        asset_ids: Target asset IDs
        strategy: Deployment strategy name
        strategy_params: Strategy-specific parameters
        user_id: User initiating deployment
        db: Database session (injected by base task)

    Returns:
        Deployment result dict
    """
    logger.info(
        f"Starting async deployment: patch={patch_id}, "
        f"assets={len(asset_ids)}, strategy={strategy}"
    )

    try:
        # Fetch patch
        patch = db.query(Patch).filter_by(id=patch_id).first()
        if not patch:
            error_msg = f"Patch {patch_id} not found"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Fetch assets
        assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
        if not assets:
            error_msg = f"No assets found with IDs: {asset_ids}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        if len(assets) != len(asset_ids):
            logger.warning(
                f"Found {len(assets)} assets, expected {len(asset_ids)}"
            )

        # Create deployment engine
        engine = DeploymentEngine(db)

        # Execute deployment
        result = engine.deploy(
            patch=patch,
            assets=assets,
            strategy=strategy,
            strategy_params=strategy_params,
            user_id=user_id
        )

        # Return result
        return {
            "success": result.success,
            "message": result.message,
            "total_assets": result.total_assets,
            "successful_assets": result.successful_assets,
            "failed_assets": result.failed_assets,
            "status": result.status.value
        }

    except Exception as e:
        logger.error(f"Deployment task error: {e}", exc_info=True)

        # Create audit log for failure
        if user_id:
            audit_log = AuditLog(
                user_id=user_id,
                action=AuditAction.DEPLOYMENT_FAILED,
                resource_type="patch",
                resource_id=patch_id,
                details={"error": str(e)},
                ip_address="internal",
                user_agent="DeploymentTask"
            )
            db.add(audit_log)
            db.commit()

        # Retry on transient errors
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            logger.info(f"Retrying deployment due to transient error: {e}")
            raise self.retry(exc=e)

        return {
            "success": False,
            "error": str(e),
            "total_assets": len(asset_ids),
            "successful_assets": 0,
            "failed_assets": len(asset_ids)
        }


@celery_app.task(
    bind=True,
    base=DeploymentTask,
    name="deployment_orchestrator.rollback_deployment",
    max_retries=2
)
def rollback_deployment(
    self,
    deployment_id: int,
    user_id: Optional[int] = None,
    db: Session = None
):
    """
    Rollback a deployment asynchronously.

    Args:
        deployment_id: Deployment to rollback
        user_id: User initiating rollback
        db: Database session (injected by base task)

    Returns:
        Rollback result dict
    """
    logger.info(f"Starting async rollback: deployment={deployment_id}")

    try:
        # Verify deployment exists
        deployment = db.query(Deployment).filter_by(id=deployment_id).first()
        if not deployment:
            error_msg = f"Deployment {deployment_id} not found"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Create engine
        engine = DeploymentEngine(db)

        # Execute rollback
        success = engine.rollback(
            deployment_id=deployment_id,
            user_id=user_id
        )

        return {
            "success": success,
            "deployment_id": deployment_id,
            "message": "Rollback completed" if success else "Rollback had errors"
        }

    except Exception as e:
        logger.error(f"Rollback task error: {e}", exc_info=True)

        if user_id:
            audit_log = AuditLog(
                user_id=user_id,
                action=AuditAction.DEPLOYMENT_ROLLBACK_FAILED,
                resource_type="deployment",
                resource_id=deployment_id,
                details={"error": str(e)},
                ip_address="internal",
                user_agent="DeploymentTask"
            )
            db.add(audit_log)
            db.commit()

        return {
            "success": False,
            "error": str(e),
            "deployment_id": deployment_id
        }


@celery_app.task(
    name="deployment_orchestrator.monitor_deployment",
    bind=True
)
def monitor_deployment(self, deployment_id: int):
    """
    Monitor ongoing deployment and update status.

    Args:
        deployment_id: Deployment to monitor

    Returns:
        Current deployment status
    """
    db = next(get_db())
    try:
        deployment = db.query(Deployment).filter_by(id=deployment_id).first()
        if not deployment:
            return {"error": "Deployment not found"}

        return {
            "id": deployment.id,
            "status": deployment.status.value,
            "total_assets": deployment.total_assets,
            "successful_assets": deployment.successful_assets,
            "failed_assets": deployment.failed_assets,
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None
        }

    finally:
        db.close()
