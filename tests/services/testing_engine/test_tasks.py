"""
Tests for testing engine Celery tasks
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.testing_engine.tasks import (
    _test_patch_async,
    _test_patches_batch_async,
    _auto_test_approved_patches_async,
)
from shared.models.models import Patch, Vulnerability, TestStatus, PatchStatus


@pytest.mark.asyncio
async def test_test_patch_task(db_session, sample_vulnerability):
    """Test test_patch task"""
    # Create a patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\napt-get install -y nginx",
        rollback_script="#!/bin/bash\napt-get install -y --allow-downgrades nginx=1.18.0-0",
        validation_script="",
        confidence_score=85,
        risk_assessment="low",
        test_status=TestStatus.NOT_TESTED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.testing_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.testing_engine.tasks.ContainerManager") as MockContainerManager:
            mock_cm_instance = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "test123"

            mock_cm_instance.create_test_environment.return_value = mock_container
            mock_cm_instance.wait_for_container_ready = AsyncMock(return_value=True)
            mock_cm_instance.cleanup_container.return_value = True

            MockContainerManager.return_value = mock_cm_instance

            with patch("services.testing_engine.tasks.TestRunner") as MockTestRunner:
                mock_runner_instance = MagicMock()
                mock_runner_instance.run_comprehensive_tests.return_value = {
                    "overall_success": True,
                    "tests_passed": 3,
                    "tests_failed": 0,
                }
                MockTestRunner.return_value = mock_runner_instance

                result = await _test_patch_async(patch.id, "comprehensive")

                assert result["status"] == "success"
                assert result["test_status"] == "passed"


@pytest.mark.asyncio
async def test_test_patch_not_found(db_session):
    """Test test_patch with non-existent patch"""
    with patch("services.testing_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _test_patch_async(99999, "comprehensive")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_test_patch_container_not_ready(db_session, sample_vulnerability):
    """Test test_patch when container fails to start"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash",
        rollback_script="#!/bin/bash",
        test_status=TestStatus.NOT_TESTED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.testing_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.testing_engine.tasks.ContainerManager") as MockContainerManager:
            mock_cm_instance = MagicMock()
            mock_container = MagicMock()

            mock_cm_instance.create_test_environment.return_value = mock_container
            mock_cm_instance.wait_for_container_ready = AsyncMock(return_value=False)  # Not ready

            MockContainerManager.return_value = mock_cm_instance

            result = await _test_patch_async(patch.id, "comprehensive")

            assert result["status"] == "error"
            assert "failed to start" in result["message"].lower()


@pytest.mark.asyncio
async def test_test_patches_batch(db_session, sample_vulnerability):
    """Test batch testing patches"""
    # Create multiple patches
    patches = []
    for i in range(3):
        patch = Patch(
            vulnerability_id=sample_vulnerability.id,
            patch_script="#!/bin/bash",
            rollback_script="#!/bin/bash",
            test_status=TestStatus.NOT_TESTED,
        )
        db_session.add(patch)
        patches.append(patch)

    await db_session.commit()

    patch_ids = [p.id for p in patches]

    with patch("services.testing_engine.tasks._test_patch_async") as mock_test:
        mock_test.return_value = {"status": "success", "test_status": "passed"}

        result = await _test_patches_batch_async(patch_ids)

        assert result["status"] == "success"
        assert result["total_patches"] == 3
        assert result["successful_tests"] == 3


@pytest.mark.asyncio
async def test_auto_test_approved_patches(db_session, sample_vulnerability):
    """Test auto-testing approved patches"""
    # Create approved patches
    for i in range(2):
        patch = Patch(
            vulnerability_id=sample_vulnerability.id,
            patch_script="#!/bin/bash",
            rollback_script="#!/bin/bash",
            status=PatchStatus.APPROVED,
            test_status=TestStatus.NOT_TESTED,
        )
        db_session.add(patch)

    await db_session.commit()

    with patch("services.testing_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.testing_engine.tasks._test_patch_async") as mock_test:
            mock_test.return_value = {"status": "success"}

            result = await _auto_test_approved_patches_async()

            assert result["status"] == "success"
            assert result["total_patches"] >= 2


@pytest.mark.asyncio
async def test_test_patch_smoke_test(db_session, sample_vulnerability):
    """Test smoke test type"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash",
        rollback_script="#!/bin/bash",
        test_status=TestStatus.NOT_TESTED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.testing_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.testing_engine.tasks.ContainerManager") as MockContainerManager:
            mock_cm_instance = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "test123"

            mock_cm_instance.create_test_environment.return_value = mock_container
            mock_cm_instance.wait_for_container_ready = AsyncMock(return_value=True)
            mock_cm_instance.cleanup_container.return_value = True

            MockContainerManager.return_value = mock_cm_instance

            with patch("services.testing_engine.tasks.TestRunner") as MockTestRunner:
                mock_runner_instance = MagicMock()
                mock_runner_instance.run_smoke_tests.return_value = {
                    "success": True,
                }
                MockTestRunner.return_value = mock_runner_instance

                result = await _test_patch_async(patch.id, "smoke")

                assert result["status"] == "success"
                assert result["test_status"] == "passed"


@pytest.mark.asyncio
async def test_test_patch_with_asset(db_session, sample_vulnerability, sample_asset):
    """Test testing patch with specific asset"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        asset_id=sample_asset.id,
        patch_script="#!/bin/bash",
        rollback_script="#!/bin/bash",
        test_status=TestStatus.NOT_TESTED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    with patch("services.testing_engine.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.testing_engine.tasks.ContainerManager") as MockContainerManager:
            mock_cm_instance = MagicMock()
            mock_container = MagicMock()

            mock_cm_instance.create_test_environment.return_value = mock_container
            mock_cm_instance.wait_for_container_ready = AsyncMock(return_value=True)
            mock_cm_instance.cleanup_container.return_value = True

            MockContainerManager.return_value = mock_cm_instance

            with patch("services.testing_engine.tasks.TestRunner") as MockTestRunner:
                mock_runner = MagicMock()
                mock_runner.run_comprehensive_tests.return_value = {
                    "overall_success": True,
                }
                MockTestRunner.return_value = mock_runner

                result = await _test_patch_async(patch.id, "comprehensive")

                # Should use asset's OS details
                assert result["status"] == "success"
