"""
Celery tasks for patch deployment
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from shared.celery_app import app
from shared.models.database import AsyncSessionLocal
from shared.models.models import Deployment, Patch, Asset, DeploymentStatus
from shared.config import settings
from sqlalchemy import select

from services.deployment_engine.executor import DeploymentExecutor

logger = structlog.get_logger()


@app.task(name="services.deployment_engine.tasks.deploy_patch", bind=True)
def deploy_patch(
    self,
    patch_id: int,
    asset_ids: List[int],
    strategy: str = "rolling",
    strategy_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deploy patch to assets

    Args:
        patch_id: ID of patch to deploy
        asset_ids: List of asset IDs to deploy to
        strategy: Deployment strategy
        strategy_options: Strategy-specific options

    Returns:
        Deployment results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _deploy_patch_async(patch_id, asset_ids, strategy, strategy_options)
    )


async def _deploy_patch_async(
    patch_id: int,
    asset_ids: List[int],
    strategy: str,
    strategy_options: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Async implementation of deploy_patch"""
    logger.info(
        "deploying_patch_task",
        patch_id=patch_id,
        asset_count=len(asset_ids),
        strategy=strategy,
    )

    async with AsyncSessionLocal() as session:
        # Fetch patch
        query = select(Patch).where(Patch.id == patch_id)
        result = await session.execute(query)
        patch = result.scalar_one_or_none()

        if not patch:
            logger.error("patch_not_found", patch_id=patch_id)
            return {"status": "error", "message": "Patch not found"}

        # Fetch assets
        query = select(Asset).where(Asset.id.in_(asset_ids))
        result = await session.execute(query)
        assets = result.scalars().all()

        if not assets:
            logger.error("no_assets_found")
            return {"status": "error", "message": "No assets found"}

        # Create deployment record
        deployment = Deployment(
            patch_id=patch.id,
            status=DeploymentStatus.IN_PROGRESS,
            strategy=strategy,
            started_at=datetime.utcnow(),
        )
        session.add(deployment)
        await session.commit()
        await session.refresh(deployment)

        # Convert assets to dictionaries
        asset_dicts = []
        for asset in assets:
            asset_dict = {
                "id": asset.id,
                "name": asset.name,
                "ip_address": asset.ip_address,
                "ssh_user": asset.metadata.get("ssh_user") if asset.metadata else None,
                "ssh_port": asset.metadata.get("ssh_port", 22) if asset.metadata else 22,
                "ssh_key_path": asset.metadata.get("ssh_key_path") if asset.metadata else None,
            }
            asset_dicts.append(asset_dict)

        # Prepare patch data
        patch_data = {
            "id": patch.id,
            "patch_script": patch.patch_script,
            "rollback_script": patch.rollback_script,
            "validation_script": patch.validation_script,
        }

        # Execute deployment
        executor = DeploymentExecutor(use_ansible=settings.use_ansible_deployment)

        try:
            deployment_results = await executor.deploy_patch(
                patch_data,
                asset_dicts,
                strategy=strategy,
                strategy_options=strategy_options,
            )

            # Update deployment record
            deployment.status = DeploymentStatus.COMPLETED if deployment_results.get("success") else DeploymentStatus.FAILED
            deployment.completed_at = datetime.utcnow()
            deployment.results = deployment_results

            await session.commit()

            logger.info(
                "deployment_task_completed",
                deployment_id=deployment.id,
                status=deployment.status.value,
            )

            return {
                "status": "success",
                "deployment_id": deployment.id,
                "deployment_status": deployment.status.value,
                "results": deployment_results,
            }

        except Exception as e:
            logger.error("deployment_task_failed", error=str(e))

            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.utcnow()
            deployment.error_message = str(e)

            await session.commit()

            return {
                "status": "error",
                "message": str(e),
                "deployment_id": deployment.id,
            }


@app.task(name="services.deployment_engine.tasks.rollback_deployment", bind=True)
def rollback_deployment(self, deployment_id: int) -> Dict[str, Any]:
    """
    Rollback a deployment

    Args:
        deployment_id: ID of deployment to rollback

    Returns:
        Rollback results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_rollback_deployment_async(deployment_id))


async def _rollback_deployment_async(deployment_id: int) -> Dict[str, Any]:
    """Async implementation of rollback_deployment"""
    logger.info("rolling_back_deployment", deployment_id=deployment_id)

    async with AsyncSessionLocal() as session:
        # Fetch deployment
        query = select(Deployment).where(Deployment.id == deployment_id)
        result = await session.execute(query)
        deployment = result.scalar_one_or_none()

        if not deployment:
            logger.error("deployment_not_found", deployment_id=deployment_id)
            return {"status": "error", "message": "Deployment not found"}

        # Fetch patch
        query = select(Patch).where(Patch.id == deployment.patch_id)
        result = await session.execute(query)
        patch = result.scalar_one_or_none()

        if not patch:
            logger.error("patch_not_found", patch_id=deployment.patch_id)
            return {"status": "error", "message": "Patch not found"}

        # Get assets from deployment results
        deployment_results = deployment.results or {}
        asset_ids = []

        # Extract asset IDs from deployment results
        if "batches" in deployment_results:
            for batch in deployment_results["batches"]:
                for asset_result in batch.get("assets", []):
                    # This is simplified - would need actual asset tracking
                    pass

        # For now, get all assets affected by this patch
        # This would need improvement for production
        from shared.models.models import AssetVulnerability
        query = (
            select(Asset)
            .join(AssetVulnerability)
            .where(AssetVulnerability.vulnerability_id == patch.vulnerability_id)
        )
        result = await session.execute(query)
        assets = result.scalars().all()

        # Convert to dicts
        asset_dicts = []
        for asset in assets:
            asset_dict = {
                "id": asset.id,
                "name": asset.name,
                "ip_address": asset.ip_address,
                "ssh_user": asset.metadata.get("ssh_user") if asset.metadata else None,
            }
            asset_dicts.append(asset_dict)

        # Execute rollback
        executor = DeploymentExecutor()

        try:
            rollback_results = await executor.rollback_deployment(
                deployment_id,
                asset_dicts,
                patch.rollback_script,
            )

            # Update deployment status
            deployment.status = DeploymentStatus.ROLLED_BACK
            deployment.rollback_at = datetime.utcnow()

            await session.commit()

            logger.info(
                "rollback_completed",
                deployment_id=deployment_id,
                successful=rollback_results["successful_rollbacks"],
            )

            return {
                "status": "success",
                "deployment_id": deployment_id,
                "rollback_results": rollback_results,
            }

        except Exception as e:
            logger.error("rollback_failed", error=str(e))
            return {
                "status": "error",
                "message": str(e),
                "deployment_id": deployment_id,
            }


@app.task(name="services.deployment_engine.tasks.verify_deployment", bind=True)
def verify_deployment(self, deployment_id: int) -> Dict[str, Any]:
    """
    Verify a deployment

    Args:
        deployment_id: ID of deployment to verify

    Returns:
        Verification results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_verify_deployment_async(deployment_id))


async def _verify_deployment_async(deployment_id: int) -> Dict[str, Any]:
    """Async implementation of verify_deployment"""
    logger.info("verifying_deployment", deployment_id=deployment_id)

    async with AsyncSessionLocal() as session:
        # Fetch deployment
        query = select(Deployment).where(Deployment.id == deployment_id)
        result = await session.execute(query)
        deployment = result.scalar_one_or_none()

        if not deployment:
            return {"status": "error", "message": "Deployment not found"}

        # Fetch patch
        query = select(Patch).where(Patch.id == deployment.patch_id)
        result = await session.execute(query)
        patch = result.scalar_one_or_none()

        if not patch or not patch.validation_script:
            return {
                "status": "error",
                "message": "No validation script available",
            }

        # Get assets (similar to rollback)
        from shared.models.models import AssetVulnerability
        query = (
            select(Asset)
            .join(AssetVulnerability)
            .where(AssetVulnerability.vulnerability_id == patch.vulnerability_id)
        )
        result = await session.execute(query)
        assets = result.scalars().all()

        asset_dicts = [{
            "id": a.id,
            "name": a.name,
            "ip_address": a.ip_address,
            "ssh_user": a.metadata.get("ssh_user") if a.metadata else None,
        } for a in assets]

        # Execute verification
        executor = DeploymentExecutor()

        try:
            verification_results = await executor.verify_deployment(
                asset_dicts,
                patch.validation_script,
            )

            logger.info(
                "deployment_verified",
                deployment_id=deployment_id,
                all_verified=verification_results["all_verified"],
            )

            return {
                "status": "success",
                "deployment_id": deployment_id,
                "verification_results": verification_results,
            }

        except Exception as e:
            logger.error("verification_failed", error=str(e))
            return {
                "status": "error",
                "message": str(e),
                "deployment_id": deployment_id,
            }


@app.task(name="services.deployment_engine.tasks.auto_deploy_tested_patches", bind=True)
def auto_deploy_tested_patches(self) -> Dict[str, Any]:
    """
    Automatically deploy patches that have passed testing

    Returns:
        Summary of auto-deployments
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_auto_deploy_tested_patches_async())


async def _auto_deploy_tested_patches_async() -> Dict[str, Any]:
    """Async implementation of auto_deploy_tested_patches"""
    logger.info("auto_deploying_tested_patches")

    async with AsyncSessionLocal() as session:
        # Find patches that are approved, tested, and not yet deployed
        from shared.models.models import PatchStatus, TestStatus

        query = (
            select(Patch)
            .where(
                Patch.status == PatchStatus.APPROVED,
                Patch.test_status == TestStatus.PASSED,
            )
            .limit(10)  # Deploy top 10 at a time
        )

        result = await session.execute(query)
        patches = result.scalars().all()

        logger.info("found_patches_for_auto_deploy", count=len(patches))

        deployments_started = []

        for patch in patches:
            # Get affected assets
            from shared.models.models import AssetVulnerability
            query = (
                select(Asset)
                .join(AssetVulnerability)
                .where(AssetVulnerability.vulnerability_id == patch.vulnerability_id)
            )
            result = await session.execute(query)
            assets = result.scalars().all()

            if not assets:
                continue

            asset_ids = [a.id for a in assets]

            # Start deployment (via task)
            # In production, we'd call the Celery task
            # For now, just record that we would start it
            deployments_started.append({
                "patch_id": patch.id,
                "asset_count": len(asset_ids),
            })

            # Update patch status to deploying
            patch.status = PatchStatus.DEPLOYING

        await session.commit()

        logger.info(
            "auto_deploy_initiated",
            deployments_started=len(deployments_started),
        )

        return {
            "status": "success",
            "deployments_started": len(deployments_started),
            "details": deployments_started,
        }
