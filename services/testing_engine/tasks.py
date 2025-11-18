"""
Celery tasks for patch testing
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from shared.celery_app import app
from shared.models.database import AsyncSessionLocal
from shared.models.models import Patch, Vulnerability, Asset, TestStatus
from shared.config import settings
from sqlalchemy import select

from services.testing_engine.container_manager import ContainerManager
from services.testing_engine.test_runner import TestRunner

logger = structlog.get_logger()


@app.task(name="services.testing_engine.tasks.test_patch", bind=True)
def test_patch(
    self,
    patch_id: int,
    test_type: str = "comprehensive",
) -> Dict[str, Any]:
    """
    Test a patch in isolated environment

    Args:
        patch_id: ID of the patch to test
        test_type: Type of test (comprehensive, smoke, security, performance)

    Returns:
        Test results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_test_patch_async(patch_id, test_type))


async def _test_patch_async(patch_id: int, test_type: str) -> Dict[str, Any]:
    """Async implementation of test_patch"""
    logger.info("testing_patch", patch_id=patch_id, test_type=test_type)

    async with AsyncSessionLocal() as session:
        # Fetch patch
        query = select(Patch).where(Patch.id == patch_id)
        result = await session.execute(query)
        patch = result.scalar_one_or_none()

        if not patch:
            logger.error("patch_not_found", patch_id=patch_id)
            return {"status": "error", "message": "Patch not found"}

        # Fetch vulnerability and asset
        query = select(Vulnerability).where(Vulnerability.id == patch.vulnerability_id)
        result = await session.execute(query)
        vulnerability = result.scalar_one_or_none()

        asset = None
        if patch.asset_id:
            query = select(Asset).where(Asset.id == patch.asset_id)
            result = await session.execute(query)
            asset = result.scalar_one_or_none()

        # Determine OS details
        if asset and asset.metadata:
            os_type = asset.metadata.get("os_type", "ubuntu")
            os_version = asset.metadata.get("os_version", "22.04")
        else:
            os_type = "ubuntu"
            os_version = "22.04"

        # Create container manager
        container_manager = ContainerManager()
        container = None

        try:
            # Create test environment
            logger.info("creating_test_environment", os_type=os_type)
            container = container_manager.create_test_environment(
                os_type=os_type,
                os_version=os_version,
                container_name=f"vulnzero-test-{patch_id}",
            )

            # Wait for container to be ready
            import asyncio
            ready = await container_manager.wait_for_container_ready(container, timeout=60)

            if not ready:
                logger.error("container_not_ready", patch_id=patch_id)
                return {"status": "error", "message": "Container failed to start"}

            # Run tests
            test_runner = TestRunner(container_manager)

            if test_type == "comprehensive":
                test_results = test_runner.run_comprehensive_tests(
                    container,
                    patch.patch_script,
                    patch.rollback_script,
                    validation_script=patch.validation_script,
                )
            elif test_type == "smoke":
                test_results = test_runner.run_smoke_tests(container)
            elif test_type == "security":
                test_results = test_runner.run_security_tests(container)
            elif test_type == "performance":
                test_results = test_runner.run_performance_tests(
                    container,
                    patch.patch_script,
                )
            else:
                test_results = {"status": "error", "message": f"Unknown test type: {test_type}"}

            # Update patch with test results
            patch.test_status = TestStatus.PASSED if test_results.get("overall_success") or test_results.get("success") else TestStatus.FAILED
            patch.test_results = test_results
            patch.tested_at = datetime.utcnow()

            await session.commit()

            logger.info(
                "patch_tested",
                patch_id=patch_id,
                test_status=patch.test_status.value,
            )

            return {
                "status": "success",
                "patch_id": patch_id,
                "test_status": patch.test_status.value,
                "test_results": test_results,
            }

        except Exception as e:
            logger.error("patch_testing_failed", error=str(e), patch_id=patch_id)
            return {
                "status": "error",
                "message": str(e),
                "patch_id": patch_id,
            }

        finally:
            # Cleanup container
            if container:
                try:
                    container_manager.cleanup_container(container)
                    logger.info("test_container_cleaned_up", patch_id=patch_id)
                except Exception as e:
                    logger.warning("container_cleanup_failed", error=str(e))


@app.task(name="services.testing_engine.tasks.test_patches_batch", bind=True)
def test_patches_batch(self, patch_ids: list[int]) -> Dict[str, Any]:
    """
    Test multiple patches in batch

    Args:
        patch_ids: List of patch IDs to test

    Returns:
        Batch test results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_test_patches_batch_async(patch_ids))


async def _test_patches_batch_async(patch_ids: list[int]) -> Dict[str, Any]:
    """Async implementation of test_patches_batch"""
    logger.info("testing_patches_batch", count=len(patch_ids))

    results = []

    for patch_id in patch_ids:
        result = await _test_patch_async(patch_id, "comprehensive")
        results.append(result)

    successful = sum(1 for r in results if r.get("status") == "success")

    logger.info(
        "batch_testing_complete",
        total=len(patch_ids),
        successful=successful,
    )

    return {
        "status": "success",
        "total_patches": len(patch_ids),
        "successful_tests": successful,
        "failed_tests": len(patch_ids) - successful,
        "results": results,
    }


@app.task(name="services.testing_engine.tasks.auto_test_approved_patches", bind=True)
def auto_test_approved_patches(self) -> Dict[str, Any]:
    """
    Automatically test all approved patches that haven't been tested yet

    Returns:
        Summary of testing
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_auto_test_approved_patches_async())


async def _auto_test_approved_patches_async() -> Dict[str, Any]:
    """Async implementation of auto_test_approved_patches"""
    logger.info("auto_testing_approved_patches")

    async with AsyncSessionLocal() as session:
        # Find approved patches that haven't been tested
        from shared.models.models import PatchStatus

        query = (
            select(Patch)
            .where(
                Patch.status == PatchStatus.APPROVED,
                Patch.test_status == TestStatus.NOT_TESTED,
            )
            .limit(10)  # Test top 10 at a time
        )

        result = await session.execute(query)
        patches = result.scalars().all()

        logger.info("found_patches_to_test", count=len(patches))

        results = []

        for patch in patches:
            result = await _test_patch_async(patch.id, "comprehensive")
            results.append(result)

        successful = sum(1 for r in results if r.get("status") == "success")

        logger.info(
            "auto_testing_complete",
            total=len(patches),
            successful=successful,
        )

        return {
            "status": "success",
            "total_patches": len(patches),
            "successful_tests": successful,
            "failed_tests": len(patches) - successful,
            "results": results,
        }


@app.task(name="services.testing_engine.tasks.verify_rollback", bind=True)
def verify_rollback(self, patch_id: int) -> Dict[str, Any]:
    """
    Verify that patch rollback works correctly

    Args:
        patch_id: ID of the patch

    Returns:
        Rollback verification results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_verify_rollback_async(patch_id))


async def _verify_rollback_async(patch_id: int) -> Dict[str, Any]:
    """Async implementation of verify_rollback"""
    logger.info("verifying_rollback", patch_id=patch_id)

    async with AsyncSessionLocal() as session:
        # Fetch patch
        query = select(Patch).where(Patch.id == patch_id)
        result = await session.execute(query)
        patch = result.scalar_one_or_none()

        if not patch:
            return {"status": "error", "message": "Patch not found"}

        # Fetch asset for OS details
        asset = None
        if patch.asset_id:
            query = select(Asset).where(Asset.id == patch.asset_id)
            result = await session.execute(query)
            asset = result.scalar_one_or_none()

        os_type = "ubuntu"
        os_version = "22.04"
        if asset and asset.metadata:
            os_type = asset.metadata.get("os_type", os_type)
            os_version = asset.metadata.get("os_version", os_version)

        # Create test environment
        container_manager = ContainerManager()
        container = None

        try:
            container = container_manager.create_test_environment(
                os_type=os_type,
                os_version=os_version,
                container_name=f"vulnzero-rollback-test-{patch_id}",
            )

            # Wait for ready
            import asyncio
            ready = await container_manager.wait_for_container_ready(container)

            if not ready:
                return {"status": "error", "message": "Container failed to start"}

            # Test rollback
            from services.testing_engine.executor import PatchExecutor
            executor = PatchExecutor(container_manager)

            rollback_result = executor.test_rollback(
                container,
                patch.patch_script,
                patch.rollback_script,
            )

            # Update patch metadata
            if not patch.metadata:
                patch.metadata = {}

            patch.metadata["rollback_verified"] = rollback_result["success"]
            patch.metadata["rollback_test_date"] = datetime.utcnow().isoformat()

            await session.commit()

            logger.info(
                "rollback_verified",
                patch_id=patch_id,
                success=rollback_result["success"],
            )

            return {
                "status": "success",
                "patch_id": patch_id,
                "rollback_works": rollback_result["success"],
                "details": rollback_result,
            }

        except Exception as e:
            logger.error("rollback_verification_failed", error=str(e))
            return {"status": "error", "message": str(e), "patch_id": patch_id}

        finally:
            if container:
                try:
                    container_manager.cleanup_container(container)
                except:
                    pass
