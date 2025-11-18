"""
Celery Tasks for Digital Twin Testing

Async tasks for patch testing in digital twins.
"""

import asyncio
import logging
from datetime import datetime

from services.digital_twin.tasks.celery_app import celery_app
from services.digital_twin.core.twin import DigitalTwin
from services.digital_twin.analyzers.result_analyzer import ResultAnalyzer
from shared.config.database import SessionLocal
from shared.models import Asset, Patch, AuditLog
from shared.models.patch import PatchStatus
from shared.models.audit_log import AuditAction, AuditResourceType

logger = logging.getLogger(__name__)


@celery_app.task(name="services.digital_twin.tasks.testing_tasks.test_patch_in_digital_twin")
def test_patch_in_digital_twin(patch_id: int, asset_id: int):
    """
    Test a patch in a digital twin environment.

    Args:
        patch_id: Patch ID to test
        asset_id: Asset ID to test on

    Returns:
        Dict with test results
    """
    return asyncio.run(_test_patch_async(patch_id, asset_id))


async def _test_patch_async(patch_id: int, asset_id: int):
    """Async implementation of patch testing"""
    db = SessionLocal()
    twin = None
    
    try:
        # Get patch and asset
        patch = db.query(Patch).filter(Patch.id == patch_id).first()
        asset = db.query(Asset).filter(Asset.id == asset_id).first()

        if not patch:
            logger.error(f"Patch {patch_id} not found")
            return {"success": False, "error": "Patch not found"}

        if not asset:
            logger.error(f"Asset {asset_id} not found")
            return {"success": False, "error": "Asset not found"}

        logger.info(f"Testing patch {patch_id} on asset {asset_id}")

        # Update patch status
        patch.test_status = "testing"
        patch.test_started_at = datetime.utcnow()
        db.commit()

        # Create digital twin
        twin = DigitalTwin(asset=asset, patch=patch)

        # Provision twin
        if not twin.provision():
            raise Exception("Failed to provision digital twin")

        # Capture state before patch
        state_before = twin.executor.get_system_state()

        # Execute patch
        exec_result = twin.execute_patch()

        # Capture state after patch
        state_after = twin.executor.get_system_state()

        # Run health checks
        health_results = twin.run_health_checks()

        # Get container logs
        logs = twin.container_manager.get_container_logs(twin.container)

        # Analyze results
        analyzer = ResultAnalyzer()
        test_result = analyzer.analyze(
            patch_id=patch_id,
            vulnerability_id=patch.vulnerability_id,
            asset_id=asset_id,
            test_id=twin.test_id,
            patch_execution=exec_result.to_dict(),
            health_checks=health_results,
            container_logs=logs,
            state_before=state_before,
            state_after=state_after,
        )

        # Update patch with test results
        patch.test_status = "passed" if test_result.overall_passed else "failed"
        patch.test_completed_at = datetime.utcnow()
        patch.test_duration_seconds = test_result.duration_seconds
        patch.test_results = {
            "status": test_result.status,
            "confidence_score": test_result.confidence_score,
            "issues": test_result.issues,
            "warnings": test_result.warnings,
            "patch_execution": test_result.patch_execution,
            "health_checks": test_result.health_checks,
        }
        patch.test_logs = logs[:10000]  # Limit to 10KB

        # Update overall patch status
        if test_result.overall_passed:
            if patch.status == PatchStatus.VALIDATED:
                patch.status = PatchStatus.TEST_PASSED
        else:
            patch.status = PatchStatus.TEST_FAILED

        # Create audit log
        audit_log = AuditLog(
            action=AuditAction.PATCH_GENERATED,
            timestamp=datetime.utcnow(),
            actor_type="system",
            actor_id="digital_twin",
            actor_name="Digital Twin Testing Engine",
            resource_type=AuditResourceType.PATCH,
            resource_id=str(patch_id),
            resource_name=patch.title,
            description=f"Digital twin test {'passed' if test_result.overall_passed else 'failed'} for patch {patch_id}",
            success=1 if test_result.overall_passed else 0,
            severity="info" if test_result.overall_passed else "warning",
            changes={
                "test_status": test_result.status,
                "confidence_score": test_result.confidence_score,
                "issues": test_result.issues,
            },
        )
        db.add(audit_log)

        db.commit()

        logger.info(f"Patch {patch_id} test completed: {test_result.status}")

        # Generate report
        report = analyzer.generate_report(test_result)
        logger.info(f"\n{report}")

        return {
            "success": True,
            "patch_id": patch_id,
            "asset_id": asset_id,
            "test_id": twin.test_id,
            "status": test_result.status,
            "overall_passed": test_result.overall_passed,
            "confidence_score": test_result.confidence_score,
            "duration_seconds": test_result.duration_seconds,
            "issues": test_result.issues,
            "warnings": test_result.warnings,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error testing patch {patch_id}: {e}", exc_info=True)

        # Update patch status to test failed
        if patch:
            patch.test_status = "failed"
            patch.test_completed_at = datetime.utcnow()
            patch.status = PatchStatus.TEST_FAILED
            db.commit()

        # Create failure audit log
        audit_log = AuditLog(
            action=AuditAction.PATCH_GENERATED,
            timestamp=datetime.utcnow(),
            actor_type="system",
            actor_id="digital_twin",
            actor_name="Digital Twin Testing Engine",
            resource_type=AuditResourceType.PATCH,
            resource_id=str(patch_id),
            description=f"Digital twin test failed with error for patch {patch_id}",
            success=0,
            severity="error",
            error_message=str(e),
        )
        db.add(audit_log)
        db.commit()

        return {"success": False, "error": str(e)}

    finally:
        # Cleanup
        if twin:
            twin.cleanup()
        db.close()


@celery_app.task(name="services.digital_twin.tasks.testing_tasks.cleanup_old_twins")
def cleanup_old_twins(max_age_hours: int = 24):
    """
    Cleanup old digital twin containers.

    Args:
        max_age_hours: Maximum age in hours

    Returns:
        Number of containers removed
    """
    try:
        from services.digital_twin.core.container import ContainerManager
        
        manager = ContainerManager()
        removed = manager.cleanup_old_containers(max_age_hours)
        
        logger.info(f"Cleaned up {removed} old digital twin containers")
        
        return {"success": True, "removed_count": removed}

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"success": False, "error": str(e)}
