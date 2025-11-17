"""
Celery Tasks for Patch Generation

Async tasks for AI-powered patch generation.
"""

import asyncio
from datetime import datetime
import logging

from services.patch_generator.tasks.celery_app import celery_app
from services.patch_generator.analyzers.vulnerability_analyzer import VulnerabilityAnalyzer
from services.patch_generator.generators.patch_generator import AIPatchGenerator
from services.patch_generator.validators.patch_validator import validate_patch
from shared.config.database import SessionLocal
from shared.models import Vulnerability, Patch, Asset, AuditLog
from shared.models.patch import PatchStatus, PatchType as PatchTypeModel
from shared.models.audit_log import AuditAction, AuditResourceType
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="services.patch_generator.tasks.generation_tasks.generate_patch_for_vulnerability")
def generate_patch_for_vulnerability(vulnerability_id: int, llm_provider: str = "openai"):
    """
    Generate patch for a specific vulnerability.

    Args:
        vulnerability_id: ID of the vulnerability
        llm_provider: LLM provider to use ("openai" or "anthropic")

    Returns:
        Dict with generation result
    """
    return asyncio.run(_generate_patch_async(vulnerability_id, llm_provider))


async def _generate_patch_async(vulnerability_id: int, llm_provider: str):
    """Async implementation of patch generation"""
    db = SessionLocal()
    try:
        # Get vulnerability
        vulnerability = db.query(Vulnerability).filter(
            Vulnerability.id == vulnerability_id
        ).first()

        if not vulnerability:
            logger.error(f"Vulnerability {vulnerability_id} not found")
            return {"success": False, "error": "Vulnerability not found"}

        logger.info(f"Generating patch for vulnerability {vulnerability.cve_id}")

        # Get asset context
        asset_context = {}
        if vulnerability.asset_id:
            asset = db.query(Asset).filter(Asset.id == vulnerability.asset_id).first()
            if asset:
                asset_context = {
                    "os_type": asset.os_type,
                    "os_version": asset.os_version,
                }

        # Analyze vulnerability
        analyzer = VulnerabilityAnalyzer()
        analysis = await analyzer.analyze(vulnerability, asset_context)

        logger.info(
            f"Analysis complete: type={analysis.patch_type.value}, "
            f"confidence={analysis.confidence:.2f}"
        )

        # Generate patch using LLM
        async with AIPatchGenerator(llm_provider=llm_provider) as generator:
            patch_result = await generator.generate_patch(vulnerability, analysis)

        logger.info(
            f"Patch generated: confidence={patch_result.confidence_score:.2f}, "
            f"tokens={patch_result.tokens_used}"
        )

        # Validate patch
        validation = validate_patch(patch_result.patch_content)

        if not validation.is_valid:
            logger.warning(
                f"Patch validation failed for {vulnerability.cve_id}: {validation.errors}"
            )

        # Store patch in database
        new_patch = Patch(
            vulnerability_id=vulnerability_id,
            title=f"AI-generated patch for {vulnerability.cve_id}",
            description=f"Generated using {llm_provider} - {patch_result.llm_model}",
            patch_type=PatchTypeModel.CODE,  # Map to appropriate type
            patch_content=patch_result.patch_content,
            rollback_script=patch_result.rollback_content,
            status=PatchStatus.VALIDATED if validation.is_valid else PatchStatus.GENERATED,
            confidence_score=patch_result.confidence_score,
            validation_score=validation.safety_score,
            llm_provider=llm_provider,
            llm_model=patch_result.llm_model,
            llm_tokens_used=patch_result.tokens_used,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_patch)

        # Create audit log
        audit_log = AuditLog(
            action=AuditAction.PATCH_GENERATED,
            timestamp=datetime.utcnow(),
            actor_type="system",
            actor_id="ai_patch_generator",
            actor_name=f"AI Patch Generator ({llm_provider})",
            resource_type=AuditResourceType.PATCH,
            resource_id=str(new_patch.id) if new_patch.id else "new",
            resource_name=new_patch.title,
            description=f"AI-generated patch for {vulnerability.cve_id} using {llm_provider}",
            success=1,
            severity="info",
            changes={
                "confidence_score": patch_result.confidence_score,
                "validation_score": validation.safety_score,
                "validation_status": "valid" if validation.is_valid else "invalid",
            },
        )
        db.add(audit_log)

        db.commit()
        db.refresh(new_patch)

        logger.info(f"Patch {new_patch.id} created for vulnerability {vulnerability.cve_id}")

        return {
            "success": True,
            "patch_id": new_patch.id,
            "vulnerability_id": vulnerability_id,
            "cve_id": vulnerability.cve_id,
            "confidence_score": patch_result.confidence_score,
            "validation_score": validation.safety_score,
            "is_valid": validation.is_valid,
            "validation_errors": validation.errors,
            "validation_warnings": validation.warnings,
            "tokens_used": patch_result.tokens_used,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error generating patch for vulnerability {vulnerability_id}: {e}", exc_info=True)

        # Create audit log for failure
        audit_log = AuditLog(
            action=AuditAction.PATCH_GENERATED,
            timestamp=datetime.utcnow(),
            actor_type="system",
            actor_id="ai_patch_generator",
            actor_name=f"AI Patch Generator ({llm_provider})",
            resource_type=AuditResourceType.PATCH,
            resource_id=str(vulnerability_id),
            description=f"Failed to generate patch for vulnerability {vulnerability_id}",
            success=0,
            severity="error",
            error_message=str(e),
        )
        db.add(audit_log)
        db.commit()

        return {"success": False, "error": str(e)}

    finally:
        db.close()


@celery_app.task(name="services.patch_generator.tasks.generation_tasks.generate_patches_for_critical_vulnerabilities")
def generate_patches_for_critical_vulnerabilities():
    """
    Generate patches for all critical vulnerabilities without patches.

    Scheduled task to automatically generate patches for high-priority vulnerabilities.
    """
    return asyncio.run(_generate_patches_for_critical_async())


async def _generate_patches_for_critical_async():
    """Async implementation"""
    db = SessionLocal()
    try:
        # Get critical vulnerabilities without patches
        critical_vulns = db.query(Vulnerability).filter(
            Vulnerability.severity.in_(["critical", "high"]),
            Vulnerability.status != "remediated",
            ~Vulnerability.patches.any()  # No patches yet
        ).limit(10).all()  # Limit to 10 to avoid overwhelming the system

        if not critical_vulns:
            logger.info("No critical vulnerabilities need patches")
            return {"success": True, "count": 0}

        logger.info(f"Generating patches for {len(critical_vulns)} critical vulnerabilities")

        # Generate patches for each
        results = []
        for vuln in critical_vulns:
            try:
                result = await _generate_patch_async(vuln.id, "openai")
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate patch for {vuln.id}: {e}")
                results.append({"success": False, "vulnerability_id": vuln.id, "error": str(e)})

        successful = sum(1 for r in results if r.get("success"))
        logger.info(f"Generated {successful}/{len(results)} patches successfully")

        return {
            "success": True,
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in batch patch generation: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
