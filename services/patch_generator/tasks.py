"""
Celery tasks for patch generation
"""

from typing import Dict, Any, Optional
import structlog

from shared.celery_app import app
from shared.models.database import AsyncSessionLocal
from shared.models.models import Vulnerability, Asset, Patch, PatchStatus
from shared.config import settings
from sqlalchemy import select

from services.patch_generator.generator import PatchGenerator

logger = structlog.get_logger()


@app.task(name="services.patch_generator.tasks.generate_patch", bind=True)
def generate_patch(
    self,
    vulnerability_id: int,
    asset_id: Optional[int] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Generate a remediation patch for a vulnerability

    Args:
        vulnerability_id: ID of the vulnerability
        asset_id: Optional ID of specific asset
        use_llm: Whether to use LLM for generation

    Returns:
        Dictionary with generation results
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _generate_patch_async(vulnerability_id, asset_id, use_llm)
    )


async def _generate_patch_async(
    vulnerability_id: int,
    asset_id: Optional[int],
    use_llm: bool,
) -> Dict[str, Any]:
    """Async implementation of generate_patch"""
    logger.info(
        "generating_patch_task",
        vulnerability_id=vulnerability_id,
        asset_id=asset_id,
        use_llm=use_llm,
    )

    async with AsyncSessionLocal() as session:
        # Fetch vulnerability
        query = select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        result = await session.execute(query)
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            logger.error("vulnerability_not_found", vulnerability_id=vulnerability_id)
            return {"status": "error", "message": "Vulnerability not found"}

        # Fetch asset if specified
        asset = None
        if asset_id:
            query = select(Asset).where(Asset.id == asset_id)
            result = await session.execute(query)
            asset = result.scalar_one_or_none()

            if not asset:
                logger.warning("asset_not_found", asset_id=asset_id)

        # Generate patch
        generator = PatchGenerator(llm_provider=settings.llm_provider)

        try:
            patch_data = await generator.generate_patch(
                vulnerability,
                asset,
                use_llm=use_llm,
            )

            # Create patch record
            patch = Patch(
                vulnerability_id=vulnerability.id,
                asset_id=asset.id if asset else None,
                patch_script=patch_data["patch_script"],
                rollback_script=patch_data["rollback_script"],
                validation_script=patch_data.get("validation_script", ""),
                confidence_score=patch_data["confidence_score"],
                risk_assessment=patch_data["risk_assessment"],
                estimated_duration_minutes=patch_data["estimated_duration_minutes"],
                requires_restart=patch_data["requires_restart"],
                affected_services=patch_data["affected_services"],
                prerequisites=patch_data.get("prerequisites", []),
                metadata={
                    "validation_result": patch_data["validation_result"],
                    "analysis": patch_data["analysis"],
                    "generation_method": patch_data["generation_method"],
                    "notes": patch_data.get("notes", ""),
                },
            )

            # Set status based on confidence and validation
            if patch_data["confidence_score"] >= 80 and patch_data["validation_result"]["is_safe"]:
                patch.status = PatchStatus.APPROVED
            elif patch_data["confidence_score"] >= 60 and patch_data["validation_result"]["is_safe"]:
                patch.status = PatchStatus.PENDING_REVIEW
            else:
                patch.status = PatchStatus.REJECTED

            session.add(patch)

            # Update vulnerability status
            if vulnerability.status == "new":
                vulnerability.status = "analyzing"

            await session.commit()
            await session.refresh(patch)

            logger.info(
                "patch_generated_task",
                patch_id=patch.id,
                vulnerability_id=vulnerability_id,
                confidence=patch_data["confidence_score"],
                status=patch.status.value,
            )

            return {
                "status": "success",
                "patch_id": patch.id,
                "vulnerability_id": vulnerability_id,
                "confidence_score": patch_data["confidence_score"],
                "risk_assessment": patch_data["risk_assessment"],
                "patch_status": patch.status.value,
            }

        except Exception as e:
            logger.error(
                "patch_generation_failed_task",
                vulnerability_id=vulnerability_id,
                error=str(e),
            )
            return {
                "status": "error",
                "message": str(e),
                "vulnerability_id": vulnerability_id,
            }


@app.task(name="services.patch_generator.tasks.generate_patches_for_vulnerability", bind=True)
def generate_patches_for_vulnerability(
    self,
    vulnerability_id: int,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Generate patches for all assets affected by a vulnerability

    Args:
        vulnerability_id: ID of the vulnerability
        use_llm: Whether to use LLM for generation

    Returns:
        Summary of patch generation
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _generate_patches_for_vulnerability_async(vulnerability_id, use_llm)
    )


async def _generate_patches_for_vulnerability_async(
    vulnerability_id: int,
    use_llm: bool,
) -> Dict[str, Any]:
    """Async implementation of generate_patches_for_vulnerability"""
    logger.info(
        "generating_patches_for_vulnerability",
        vulnerability_id=vulnerability_id,
    )

    async with AsyncSessionLocal() as session:
        # Fetch vulnerability with affected assets
        query = select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        result = await session.execute(query)
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            return {"status": "error", "message": "Vulnerability not found"}

        # Get affected assets
        from shared.models.models import AssetVulnerability
        query = (
            select(Asset)
            .join(AssetVulnerability)
            .where(AssetVulnerability.vulnerability_id == vulnerability_id)
        )
        result = await session.execute(query)
        assets = result.scalars().all()

        logger.info(
            "found_affected_assets",
            vulnerability_id=vulnerability_id,
            asset_count=len(assets),
        )

        # Generate patches for each asset
        generator = PatchGenerator(llm_provider=settings.llm_provider)
        results = []

        for asset in assets:
            try:
                patch_data = await generator.generate_patch(
                    vulnerability,
                    asset,
                    use_llm=use_llm,
                )

                # Create patch record
                patch = Patch(
                    vulnerability_id=vulnerability.id,
                    asset_id=asset.id,
                    patch_script=patch_data["patch_script"],
                    rollback_script=patch_data["rollback_script"],
                    validation_script=patch_data.get("validation_script", ""),
                    confidence_score=patch_data["confidence_score"],
                    risk_assessment=patch_data["risk_assessment"],
                    estimated_duration_minutes=patch_data["estimated_duration_minutes"],
                    requires_restart=patch_data["requires_restart"],
                    affected_services=patch_data["affected_services"],
                    prerequisites=patch_data.get("prerequisites", []),
                    metadata={
                        "validation_result": patch_data["validation_result"],
                        "analysis": patch_data["analysis"],
                        "generation_method": patch_data["generation_method"],
                    },
                )

                # Auto-approve high-confidence safe patches
                if patch_data["confidence_score"] >= 80 and patch_data["validation_result"]["is_safe"]:
                    patch.status = PatchStatus.APPROVED
                else:
                    patch.status = PatchStatus.PENDING_REVIEW

                session.add(patch)

                results.append({
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "confidence": patch_data["confidence_score"],
                    "status": "success",
                })

            except Exception as e:
                logger.error(
                    "patch_generation_failed_for_asset",
                    asset_id=asset.id,
                    error=str(e),
                )
                results.append({
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "status": "error",
                    "error": str(e),
                })

        await session.commit()

        successful = sum(1 for r in results if r["status"] == "success")

        logger.info(
            "patches_generated_for_vulnerability",
            vulnerability_id=vulnerability_id,
            total_assets=len(assets),
            successful=successful,
        )

        return {
            "status": "success",
            "vulnerability_id": vulnerability_id,
            "total_assets": len(assets),
            "successful_patches": successful,
            "failed_patches": len(assets) - successful,
            "results": results,
        }


@app.task(name="services.patch_generator.tasks.regenerate_patch", bind=True)
def regenerate_patch(self, patch_id: int) -> Dict[str, Any]:
    """
    Regenerate a patch that failed validation

    Args:
        patch_id: ID of the patch to regenerate

    Returns:
        Results of regeneration
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_regenerate_patch_async(patch_id))


async def _regenerate_patch_async(patch_id: int) -> Dict[str, Any]:
    """Async implementation of regenerate_patch"""
    logger.info("regenerating_patch", patch_id=patch_id)

    async with AsyncSessionLocal() as session:
        # Fetch patch
        query = select(Patch).where(Patch.id == patch_id)
        result = await session.execute(query)
        patch = result.scalar_one_or_none()

        if not patch:
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

        # Get previous validation results
        previous_validation = patch.metadata.get("validation_result", {})

        # Regenerate with LLM
        generator = PatchGenerator(llm_provider=settings.llm_provider)

        try:
            patch_data = await generator.regenerate_patch_with_fixes(
                vulnerability,
                asset,
                previous_validation,
            )

            # Update patch record
            patch.patch_script = patch_data["patch_script"]
            patch.rollback_script = patch_data["rollback_script"]
            patch.validation_script = patch_data.get("validation_script", "")
            patch.confidence_score = patch_data["confidence_score"]
            patch.risk_assessment = patch_data["risk_assessment"]
            patch.metadata.update({
                "validation_result": patch_data["validation_result"],
                "regeneration_count": patch.metadata.get("regeneration_count", 0) + 1,
            })

            # Update status
            if patch_data["confidence_score"] >= 80 and patch_data["validation_result"]["is_safe"]:
                patch.status = PatchStatus.APPROVED
            else:
                patch.status = PatchStatus.PENDING_REVIEW

            await session.commit()

            logger.info(
                "patch_regenerated",
                patch_id=patch_id,
                new_confidence=patch_data["confidence_score"],
            )

            return {
                "status": "success",
                "patch_id": patch_id,
                "confidence_score": patch_data["confidence_score"],
                "patch_status": patch.status.value,
            }

        except Exception as e:
            logger.error("patch_regeneration_failed", patch_id=patch_id, error=str(e))
            return {"status": "error", "message": str(e), "patch_id": patch_id}


@app.task(name="services.patch_generator.tasks.auto_generate_patches", bind=True)
def auto_generate_patches(self, min_priority: float = 70.0) -> Dict[str, Any]:
    """
    Automatically generate patches for high-priority vulnerabilities

    Args:
        min_priority: Minimum priority score to generate patches for

    Returns:
        Summary of auto-generation
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_auto_generate_patches_async(min_priority))


async def _auto_generate_patches_async(min_priority: float) -> Dict[str, Any]:
    """Async implementation of auto_generate_patches"""
    logger.info("auto_generating_patches", min_priority=min_priority)

    async with AsyncSessionLocal() as session:
        # Find high-priority vulnerabilities without patches
        query = (
            select(Vulnerability)
            .where(
                Vulnerability.status.in_(["new", "analyzing"]),
                Vulnerability.priority_score >= min_priority,
            )
            .order_by(Vulnerability.priority_score.desc())
            .limit(50)  # Process top 50 at a time
        )
        result = await session.execute(query)
        vulnerabilities = result.scalars().all()

        logger.info(
            "found_high_priority_vulnerabilities",
            count=len(vulnerabilities),
            min_priority=min_priority,
        )

        results = []
        generator = PatchGenerator(llm_provider=settings.llm_provider)

        for vuln in vulnerabilities:
            try:
                # Generate generic patch for vulnerability
                patch_data = await generator.generate_patch(
                    vuln,
                    asset=None,
                    use_llm=True,
                )

                # Create patch record
                patch = Patch(
                    vulnerability_id=vuln.id,
                    asset_id=None,  # Generic patch
                    patch_script=patch_data["patch_script"],
                    rollback_script=patch_data["rollback_script"],
                    validation_script=patch_data.get("validation_script", ""),
                    confidence_score=patch_data["confidence_score"],
                    risk_assessment=patch_data["risk_assessment"],
                    estimated_duration_minutes=patch_data["estimated_duration_minutes"],
                    requires_restart=patch_data["requires_restart"],
                    affected_services=patch_data["affected_services"],
                    prerequisites=patch_data.get("prerequisites", []),
                    metadata={"auto_generated": True},
                )

                if patch_data["confidence_score"] >= 80 and patch_data["validation_result"]["is_safe"]:
                    patch.status = PatchStatus.APPROVED
                else:
                    patch.status = PatchStatus.PENDING_REVIEW

                session.add(patch)

                results.append({
                    "vulnerability_id": vuln.id,
                    "cve_id": vuln.cve_id,
                    "priority": vuln.priority_score,
                    "confidence": patch_data["confidence_score"],
                    "status": "success",
                })

            except Exception as e:
                logger.error(
                    "auto_patch_generation_failed",
                    vulnerability_id=vuln.id,
                    error=str(e),
                )
                results.append({
                    "vulnerability_id": vuln.id,
                    "cve_id": vuln.cve_id,
                    "status": "error",
                    "error": str(e),
                })

        await session.commit()

        successful = sum(1 for r in results if r["status"] == "success")

        logger.info(
            "auto_patches_generated",
            total=len(vulnerabilities),
            successful=successful,
        )

        return {
            "status": "success",
            "total_vulnerabilities": len(vulnerabilities),
            "successful_patches": successful,
            "failed_patches": len(vulnerabilities) - successful,
            "results": results,
        }
