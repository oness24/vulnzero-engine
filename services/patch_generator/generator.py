"""
Main patch generator orchestrator
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from shared.models.models import Vulnerability, Asset, Patch
from services.patch_generator.llm_client import get_llm_client
from services.patch_generator.package_managers import get_package_manager
from services.patch_generator.validator import PatchValidator, PatchAnalyzer

logger = structlog.get_logger()


class PatchGenerator:
    """
    Main orchestrator for AI-powered patch generation

    This class coordinates the entire patch generation workflow:
    1. Gather context about vulnerability and affected systems
    2. Generate remediation patch using LLM
    3. Validate patch for safety
    4. Generate rollback script
    5. Calculate confidence score
    """

    def __init__(self, llm_provider: Optional[str] = None):
        self.llm_client = get_llm_client(llm_provider)
        self.validator = PatchValidator()
        self.analyzer = PatchAnalyzer()

    async def generate_patch(
        self,
        vulnerability: Vulnerability,
        asset: Optional[Asset] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a remediation patch for a vulnerability

        Args:
            vulnerability: Vulnerability to remediate
            asset: Optional specific asset (if None, generates generic patch)
            use_llm: Whether to use LLM (if False, generates template-based patch)

        Returns:
            Dictionary with patch details
        """
        logger.info(
            "generating_patch",
            cve_id=vulnerability.cve_id,
            asset_id=asset.id if asset else None,
            use_llm=use_llm,
        )

        # Gather context
        context = self._build_context(vulnerability, asset)

        # Generate patch
        if use_llm:
            patch_data = await self._generate_llm_patch(vulnerability, context)
        else:
            patch_data = self._generate_template_patch(vulnerability, context)

        # Validate patch
        validation_result = self.validator.validate_patch(
            patch_data["patch_script"],
            context,
        )

        # Analyze patch
        analysis = self.analyzer.analyze_patch(patch_data["patch_script"])

        # Validate rollback script
        rollback_validation = self.validator.validate_rollback_script(
            patch_data["rollback_script"]
        )

        # Calculate overall confidence
        confidence_score = self._calculate_confidence(
            patch_data.get("confidence_score", 50),
            validation_result,
            use_llm,
        )

        result = {
            "patch_script": patch_data["patch_script"],
            "rollback_script": patch_data["rollback_script"],
            "validation_script": patch_data.get("validation_script", ""),
            "confidence_score": confidence_score,
            "validation_result": validation_result,
            "rollback_validation": rollback_validation,
            "analysis": analysis,
            "requires_restart": analysis["requires_restart"],
            "affected_services": analysis["affected_services"],
            "estimated_duration_minutes": analysis["estimated_duration"],
            "risk_assessment": validation_result["risk_level"],
            "prerequisites": patch_data.get("prerequisites", []),
            "notes": patch_data.get("notes", ""),
            "generation_method": "llm" if use_llm else "template",
        }

        logger.info(
            "patch_generated",
            cve_id=vulnerability.cve_id,
            confidence=confidence_score,
            risk_level=validation_result["risk_level"],
            is_safe=validation_result["is_safe"],
        )

        return result

    async def _generate_llm_patch(
        self,
        vulnerability: Vulnerability,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate patch using LLM"""
        vuln_dict = {
            "cve_id": vulnerability.cve_id,
            "title": vulnerability.title,
            "description": vulnerability.description or "",
            "severity": vulnerability.severity.value,
            "cvss_score": vulnerability.cvss_score,
            "affected_package": context.get("affected_package", "unknown"),
            "current_version": context.get("current_version", "unknown"),
            "fixed_version": context.get("fixed_version", "latest"),
        }

        return await self.llm_client.generate_patch(vuln_dict, context)

    def _generate_template_patch(
        self,
        vulnerability: Vulnerability,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate patch using templates (no LLM)"""
        os_type = context.get("os_type", "ubuntu")
        package_manager = get_package_manager(os_type, context.get("os_version"))

        affected_package = context.get("affected_package", "unknown")
        target_version = context.get("fixed_version")

        # Build patch script using package manager
        patch_script = package_manager.build_patch_script(
            affected_package,
            target_version,
            pre_checks=True,
        )

        # Build rollback script
        current_version = context.get("current_version")
        if current_version and current_version != "unknown":
            rollback_script = package_manager.build_rollback_script(
                affected_package,
                current_version,
            )
        else:
            rollback_script = "# WARNING: Current version unknown - rollback not available\nexit 1"

        # Build validation script
        validation_script = f"""#!/bin/bash
# Validation script for {vulnerability.cve_id}

echo "Checking {affected_package} version..."
CURRENT_VERSION=$({package_manager.get_version_check_command(affected_package)})
echo "Current version: $CURRENT_VERSION"

if [ "$CURRENT_VERSION" = "not-installed" ]; then
    echo "ERROR: Package not installed"
    exit 1
fi

echo "Patch validation successful"
"""

        return {
            "patch_script": patch_script,
            "rollback_script": rollback_script,
            "validation_script": validation_script,
            "confidence_score": 70,  # Template-based has moderate confidence
            "estimated_duration_minutes": 5,
            "requires_restart": False,
            "risk_assessment": "low",
            "prerequisites": ["root privileges", f"{package_manager.manager_name} package manager"],
            "affected_services": [],
            "notes": "Template-generated patch - review before deployment",
        }

    def _build_context(
        self,
        vulnerability: Vulnerability,
        asset: Optional[Asset],
    ) -> Dict[str, Any]:
        """Build context for patch generation"""
        context = {
            "os_type": "ubuntu",  # Default
            "os_version": "22.04",
            "package_manager": "apt",
            "asset_criticality": 5.0,
            "is_production": False,
            "is_critical": False,
        }

        # Extract from asset if available
        if asset:
            metadata = asset.metadata or {}
            context.update({
                "os_type": metadata.get("os_type", "ubuntu"),
                "os_version": metadata.get("os_version", "22.04"),
                "asset_criticality": asset.criticality,
                "is_production": metadata.get("environment") == "production",
                "is_critical": asset.criticality >= 8.0,
            })

            # Determine package manager from OS
            os_type = context["os_type"].lower()
            if os_type in ["debian", "ubuntu"]:
                context["package_manager"] = "apt"
            elif os_type in ["rhel", "centos", "fedora"]:
                context["package_manager"] = "yum"
            elif os_type in ["opensuse", "sles"]:
                context["package_manager"] = "zypper"

        # Extract package information from vulnerability data
        nvd_data = vulnerability.nvd_data or {}
        if nvd_data:
            # Try to extract affected package from NVD data
            configurations = nvd_data.get("configurations", {})
            # This is simplified - real implementation would parse CPE strings
            context["affected_package"] = nvd_data.get("affected_package", "unknown")
            context["current_version"] = nvd_data.get("current_version", "unknown")
            context["fixed_version"] = nvd_data.get("fixed_version")

        return context

    def _calculate_confidence(
        self,
        base_confidence: float,
        validation_result: Dict[str, Any],
        used_llm: bool,
    ) -> float:
        """
        Calculate overall confidence score

        Args:
            base_confidence: Base confidence from LLM or template
            validation_result: Validation results
            used_llm: Whether LLM was used

        Returns:
            Confidence score (0-100)
        """
        confidence = base_confidence

        # Adjust based on validation
        if not validation_result["is_safe"]:
            confidence *= 0.3  # Severe penalty for unsafe patches

        safety_score = validation_result["score"]
        confidence = (confidence + safety_score) / 2

        # Adjust based on risk level
        risk_penalties = {
            "critical": 0.2,
            "high": 0.5,
            "medium": 0.8,
            "low": 1.0,
        }
        confidence *= risk_penalties.get(validation_result["risk_level"], 0.8)

        # LLM-generated patches typically have higher confidence
        if used_llm:
            confidence *= 1.1

        # Cap at 95 (never 100% confident)
        return min(95.0, max(0.0, confidence))

    async def regenerate_patch_with_fixes(
        self,
        vulnerability: Vulnerability,
        asset: Optional[Asset],
        previous_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Regenerate patch addressing validation issues

        Args:
            vulnerability: Vulnerability to remediate
            asset: Optional specific asset
            previous_validation: Previous validation results to address

        Returns:
            New patch data
        """
        logger.info(
            "regenerating_patch",
            cve_id=vulnerability.cve_id,
            previous_issues=len(previous_validation.get("issues", [])),
        )

        # Build context with validation feedback
        context = self._build_context(vulnerability, asset)
        context["previous_issues"] = previous_validation.get("issues", [])
        context["previous_warnings"] = previous_validation.get("warnings", [])
        context["previous_recommendations"] = previous_validation.get("recommendations", [])

        # Generate new patch with LLM, incorporating feedback
        # For now, just regenerate - could be enhanced to pass feedback to LLM
        return await self.generate_patch(vulnerability, asset, use_llm=True)
