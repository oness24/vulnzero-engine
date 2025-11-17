"""Main patch generator service."""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from vulnzero.shared.models import Patch, PatchStatus, PatchType, Vulnerability

from .cve_fetcher import CVEData, CVEFetcher
from .llm_client import LLMClient, get_llm_client
from .prompts import get_package_update_prompt, get_rollback_prompt
from .validator import PatchValidator, ValidationResult


@dataclass
class PatchGenerationResult:
    """Result of patch generation."""

    success: bool
    patch: Optional[Patch]
    error_message: Optional[str]
    validation_result: Optional[ValidationResult]
    cve_data: Optional[CVEData]


class PatchGenerator:
    """Main service for generating vulnerability remediation patches."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        cve_fetcher: Optional[CVEFetcher] = None,
        validator: Optional[PatchValidator] = None,
    ):
        """
        Initialize patch generator.

        Args:
            llm_client: LLM client (uses default from settings if not provided)
            cve_fetcher: CVE data fetcher (creates new if not provided)
            validator: Patch validator (creates new if not provided)
        """
        self.llm_client = llm_client or get_llm_client()
        self.cve_fetcher = cve_fetcher or CVEFetcher()
        self.validator = validator or PatchValidator()

    def generate_patch(
        self,
        vulnerability: Vulnerability,
        os_type: str = "ubuntu",
        os_version: str = "22.04",
        patch_type: str = PatchType.PACKAGE_UPDATE,
    ) -> PatchGenerationResult:
        """
        Generate a remediation patch for a vulnerability.

        Args:
            vulnerability: Vulnerability model instance
            os_type: Operating system type
            os_version: Operating system version
            patch_type: Type of patch to generate

        Returns:
            PatchGenerationResult with generated patch or error
        """
        try:
            # 1. Fetch CVE data from NVD
            cve_data = self.cve_fetcher.fetch_cve(vulnerability.cve_id)
            if not cve_data:
                return PatchGenerationResult(
                    success=False,
                    patch=None,
                    error_message=f"CVE data not found for {vulnerability.cve_id}",
                    validation_result=None,
                    cve_data=None,
                )

            # 2. Prepare context for LLM
            context = self._prepare_context(vulnerability, cve_data, os_type, os_version)

            # 3. Generate prompt based on patch type
            if patch_type == PatchType.PACKAGE_UPDATE:
                prompt = get_package_update_prompt(context)
            else:
                # TODO: Add other patch types
                prompt = get_package_update_prompt(context)

            # 4. Generate patch using LLM
            patch_content = self.llm_client.generate(
                prompt=prompt, max_tokens=2000, temperature=0.2
            )

            # 5. Clean up the response (remove markdown code blocks if present)
            patch_content = self._extract_script_from_response(patch_content)

            # 6. Validate the generated patch
            validation_result = self.validator.validate(patch_content)

            # 7. Generate rollback script
            rollback_script = None
            if validation_result.syntax_valid:
                rollback_prompt = get_rollback_prompt(patch_content, context)
                rollback_script = self.llm_client.generate(
                    prompt=rollback_prompt, max_tokens=1000, temperature=0.2
                )
                rollback_script = self._extract_script_from_response(rollback_script)

            # 8. Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                validation_result, cve_data, len(patch_content)
            )

            # 9. Create Patch model instance
            patch = Patch(
                patch_id=f"patch_{uuid.uuid4().hex[:12]}",
                vulnerability_id=vulnerability.id,
                patch_type=patch_type,
                status=PatchStatus.VALIDATED
                if validation_result.is_valid
                else PatchStatus.VALIDATION_FAILED,
                patch_content=patch_content,
                rollback_script=rollback_script,
                llm_model=self.llm_client.get_model_name(),
                llm_prompt=prompt,
                llm_response=patch_content,
                confidence_score=confidence_score,
                validation_result=str(
                    {
                        "is_valid": validation_result.is_valid,
                        "safety_score": validation_result.safety_score,
                        "issues_count": len(validation_result.issues),
                        "dangerous_commands": validation_result.dangerous_commands,
                    }
                ),
                syntax_check_passed=validation_result.syntax_valid,
                security_check_passed=len(validation_result.dangerous_commands) == 0,
            )

            return PatchGenerationResult(
                success=True,
                patch=patch,
                error_message=None,
                validation_result=validation_result,
                cve_data=cve_data,
            )

        except Exception as e:
            return PatchGenerationResult(
                success=False,
                patch=None,
                error_message=f"Patch generation failed: {str(e)}",
                validation_result=None,
                cve_data=None,
            )

    def _prepare_context(
        self, vulnerability: Vulnerability, cve_data: CVEData, os_type: str, os_version: str
    ) -> Dict:
        """Prepare context dictionary for prompt generation."""
        # Get package manager for OS
        package_manager = self.cve_fetcher.get_package_manager_for_os(os_type)

        # Extract affected packages
        affected_packages = self.cve_fetcher.extract_affected_packages(cve_data)
        primary_package = affected_packages[0] if affected_packages else {}

        return {
            "cve_id": vulnerability.cve_id,
            "description": cve_data.description,
            "package_name": vulnerability.package_name
            or primary_package.get("product", "unknown"),
            "vulnerable_version": vulnerability.vulnerable_version
            or primary_package.get("version", "unknown"),
            "fixed_version": vulnerability.fixed_version or "latest",
            "os_type": os_type,
            "os_version": os_version,
            "package_manager": package_manager,
            "severity": vulnerability.severity,
            "cvss_score": vulnerability.cvss_score or cve_data.cvss_score,
        }

    def _extract_script_from_response(self, response: str) -> str:
        """Extract bash script from LLM response (remove markdown code blocks)."""
        # Remove markdown code blocks if present
        if "```bash" in response:
            # Extract content between ```bash and ```
            start = response.find("```bash") + 7
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()

        if "```sh" in response:
            start = response.find("```sh") + 5
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()

        if "```" in response:
            # Generic code block
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()

        return response.strip()

    def _calculate_confidence_score(
        self, validation_result: ValidationResult, cve_data: CVEData, script_length: int
    ) -> float:
        """
        Calculate confidence score for the generated patch.

        Args:
            validation_result: Validation result
            cve_data: CVE data
            script_length: Length of generated script

        Returns:
            Confidence score from 0.0 to 1.0
        """
        score = 0.0

        # Base score from validation (40% weight)
        score += validation_result.safety_score * 0.4

        # Syntax validity (20% weight)
        if validation_result.syntax_valid:
            score += 0.2

        # CVE severity affects confidence - well-known critical CVEs have more tested patterns (15% weight)
        if cve_data.cvss_score:
            if cve_data.cvss_score >= 7.0:  # High/Critical
                score += 0.15
            else:
                score += 0.10

        # Script complexity - simpler is more confident (15% weight)
        # Ideal script length: 100-300 lines
        if 50 < script_length < 500:
            score += 0.15
        elif script_length <= 50 or script_length >= 1000:
            score += 0.05
        else:
            score += 0.10

        # No dangerous commands (10% weight)
        if len(validation_result.dangerous_commands) == 0:
            score += 0.10

        return min(1.0, max(0.0, score))

    def close(self) -> None:
        """Clean up resources."""
        if self.cve_fetcher:
            self.cve_fetcher.close()
