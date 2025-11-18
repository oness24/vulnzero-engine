"""
Tests for deployment engine Celery tasks
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.deployment_engine.tasks import (
    _deploy_patch_async,
    _rollback_deployment_async,
    _verify_deployment_async,
)
from shared.models.models import Deployment, Patch, Asset, DeploymentStatus, PatchStatus


@pytest.mark.asyncio
async def test_deploy_patch_task(db_session, sample_vulnerability, sample_asset):
    """Test deploy_patch task"""
    # Create patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.deployment_engine.tasks.DeploymentExecutor") as MockExecutor:
            mock_executor = MagicMock()
            mock_executor.deploy_patch = AsyncMock(return_value={
                "success": True,
                "successful": 1,
                "failed": 0,
            })
            MockExecutor.return_value = mock_executor

            result = await _deploy_patch_async(
                patch.id,
                [sample_asset.id],
                "rolling",
                None,
            )

            assert result["status"] == "success"
            assert "deployment_id" in result


@pytest.mark.asyncio
async def test_deploy_patch_not_found(db_session):
    """Test deploy_patch with non-existent patch"""
    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _deploy_patch_async(99999, [1], "rolling", None)

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_deploy_patch_no_assets(db_session, sample_vulnerability):
    """Test deploy_patch with no assets found"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _deploy_patch_async(patch.id, [99999], "rolling", None)

        assert result["status"] == "error"
        assert "no assets" in result["message"].lower()


@pytest.mark.asyncio
async def test_deploy_patch_failure(db_session, sample_vulnerability, sample_asset):
    """Test deploy_patch with deployment failure"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.deployment_engine.tasks.DeploymentExecutor") as MockExecutor:
            mock_executor = MagicMock()
            mock_executor.deploy_patch = AsyncMock(side_effect=Exception("Deployment error"))
            MockExecutor.return_value = mock_executor

            result = await _deploy_patch_async(patch.id, [sample_asset.id], "rolling", None)

            assert result["status"] == "error"


@pytest.mark.asyncio
async def test_rollback_deployment_task(db_session, sample_vulnerability, sample_asset):
    """Test rollback_deployment task"""
    # Create patch and deployment
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.COMPLETED,
        strategy="rolling",
        results={},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.deployment_engine.tasks.DeploymentExecutor") as MockExecutor:
            mock_executor = MagicMock()
            mock_executor.rollback_deployment = AsyncMock(return_value={
                "successful_rollbacks": 1,
                "failed_rollbacks": 0,
            })
            MockExecutor.return_value = mock_executor

            result = await _rollback_deployment_async(deployment.id)

            assert result["status"] == "success"


@pytest.mark.asyncio
async def test_verify_deployment_task(db_session, sample_vulnerability, sample_asset):
    """Test verify_deployment task"""
    # Create patch and deployment
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
        validation_script="#!/bin/bash\necho verify",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.COMPLETED,
        strategy="rolling",
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.deployment_engine.tasks.DeploymentExecutor") as MockExecutor:
            mock_executor = MagicMock()
            mock_executor.verify_deployment = AsyncMock(return_value={
                "all_verified": True,
                "verified": 1,
                "failed": 0,
            })
            MockExecutor.return_value = mock_executor

            result = await _verify_deployment_async(deployment.id)

            assert result["status"] == "success"


@pytest.mark.asyncio
async def test_verify_deployment_no_validation_script(db_session, sample_vulnerability):
    """Test verify_deployment without validation script"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
        validation_script=None,  # No validation script
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.COMPLETED,
        strategy="rolling",
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.deployment_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _verify_deployment_async(deployment.id)

        assert result["status"] == "error"
        assert "validation script" in result["message"].lower()
