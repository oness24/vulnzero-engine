"""
AI Patch Generator

Uses LLMs to generate remediation scripts based on vulnerability analysis.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from services.patch_generator.llm.factory import get_llm_client
from services.patch_generator.llm.base import LLMMessage
from services.patch_generator.analyzers.vulnerability_analyzer import (
    AnalysisResult,
    PatchType,
    PackageManager,
)
from shared.models import Vulnerability, Patch
from shared.models.patch import PatchStatus, PatchType as PatchTypeModel

logger = logging.getLogger(__name__)


class PatchGenerationResult:
    """Result of patch generation"""
    def __init__(
        self,
        patch_content: str,
        rollback_content: str,
        confidence_score: float,
        llm_provider: str,
        llm_model: str,
        tokens_used: int,
        metadata: Dict[str, Any] = None
    ):
        self.patch_content = patch_content
        self.rollback_content = rollback_content
        self.confidence_score = confidence_score
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.tokens_used = tokens_used
        self.metadata = metadata or {}


class AIPatchGenerator:
    """
    AI-powered patch generator using LLMs.
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_api_key: Optional[str] = None,
        llm_model: Optional[str] = None
    ):
        """
        Initialize AI patch generator.

        Args:
            llm_provider: LLM provider ("openai" or "anthropic")
            llm_api_key: API key (if None, uses environment variable)
            llm_model: Specific model to use
        """
        self.llm_provider = llm_provider
        self.llm_client = get_llm_client(llm_provider, llm_api_key, llm_model)
        self.logger = logging.getLogger(__name__)

    async def generate_patch(
        self,
        vulnerability: Vulnerability,
        analysis: AnalysisResult
    ) -> PatchGenerationResult:
        """
        Generate patch for a vulnerability.

        Args:
            vulnerability: Vulnerability model
            analysis: Analysis result from VulnerabilityAnalyzer

        Returns:
            PatchGenerationResult with generated patch
        """
        self.logger.info(f"Generating patch for {vulnerability.cve_id} using {self.llm_provider}")

        # Build system prompt based on patch type
        system_prompt = self._build_system_prompt(analysis.patch_type, analysis.package_manager)

        # Build user prompt with vulnerability details
        user_prompt = self._build_user_prompt(vulnerability, analysis)

        # Generate patch using LLM
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_client.generate_with_retry(
            messages=messages,
            temperature=0.3,  # Lower temperature for more deterministic output
            max_tokens=2000,
        )

        # Parse response to extract patch and rollback scripts
        patch_content, rollback_content = self._parse_llm_response(response.content)

        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            analysis, response, patch_content
        )

        result = PatchGenerationResult(
            patch_content=patch_content,
            rollback_content=rollback_content,
            confidence_score=confidence_score,
            llm_provider=self.llm_provider,
            llm_model=response.model,
            tokens_used=response.tokens_used,
            metadata={
                "analysis_confidence": analysis.confidence,
                "patch_type": analysis.patch_type.value,
                "package_manager": analysis.package_manager.value,
                "complexity": analysis.complexity,
            }
        )

        self.logger.info(
            f"Generated patch for {vulnerability.cve_id}: "
            f"confidence={confidence_score:.2f}, tokens={response.tokens_used}"
        )

        return result

    def _build_system_prompt(
        self,
        patch_type: PatchType,
        package_manager: PackageManager
    ) -> str:
        """Build system prompt based on patch type"""

        if patch_type == PatchType.PACKAGE_UPDATE:
            return self._get_package_update_prompt(package_manager)
        elif patch_type == PatchType.CONFIG_CHANGE:
            return self._get_config_change_prompt()
        elif patch_type == PatchType.WORKAROUND:
            return self._get_workaround_prompt()
        elif patch_type == PatchType.KERNEL_PATCH:
            return self._get_kernel_patch_prompt()
        else:
            return self._get_default_prompt()

    def _get_package_update_prompt(self, package_manager: PackageManager) -> str:
        """System prompt for package updates"""
        pm_commands = {
            PackageManager.APT: "apt-get update && apt-get install -y",
            PackageManager.YUM: "yum update -y",
            PackageManager.DNF: "dnf update -y",
            PackageManager.ZYPPER: "zypper update -y",
        }

        pm_cmd = pm_commands.get(package_manager, "# Package manager commands")

        return f"""You are a Linux system administrator and security expert. Generate safe, production-ready remediation scripts.

Your task is to create a bash script to patch a vulnerability by updating packages using {package_manager.value}.

REQUIREMENTS:
1. Use {pm_cmd} for package updates
2. Include error checking (set -e, set -u, set -o pipefail)
3. Add logging with timestamps
4. Check if running as root
5. Create backup of package state before update
6. Verify package installation after update
7. Include rollback script

FORMAT YOUR RESPONSE AS:
```bash
# PATCH SCRIPT
<your patch script here>
```

```bash
# ROLLBACK SCRIPT
<your rollback script here>
```

Make scripts idempotent and safe for production use."""

    def _get_config_change_prompt(self) -> str:
        """System prompt for configuration changes"""
        return """You are a Linux system administrator and security expert. Generate safe configuration change scripts.

Your task is to create a bash script to remediate a vulnerability by modifying system configuration.

REQUIREMENTS:
1. Backup original configuration files before modification
2. Validate configuration syntax after changes
3. Use sed/awk for safe in-place editing
4. Include error checking
5. Test configuration before applying
6. Restart affected services gracefully
7. Include rollback to restore original configuration

FORMAT YOUR RESPONSE AS:
```bash
# PATCH SCRIPT
<your configuration change script>
```

```bash
# ROLLBACK SCRIPT
<script to restore original configuration>
```

Make scripts idempotent and production-safe."""

    def _get_workaround_prompt(self) -> str:
        """System prompt for workarounds"""
        return """You are a Linux system administrator and security expert. Generate safe workaround scripts.

Your task is to create a temporary workaround script to mitigate a vulnerability until a proper patch is available.

REQUIREMENTS:
1. Implement least-privilege temporary fixes
2. Add monitoring/alerting for workaround status
3. Include expiration/reminder mechanisms
4. Document why workaround is needed
5. Make workaround reversible
6. Minimize performance impact

FORMAT YOUR RESPONSE AS:
```bash
# WORKAROUND SCRIPT
<your workaround script>
```

```bash
# REMOVAL SCRIPT
<script to remove workaround>
```"""

    def _get_kernel_patch_prompt(self) -> str:
        """System prompt for kernel patches"""
        return """You are a Linux system administrator and security expert. Generate safe kernel update procedures.

Your task is to create a procedure for updating the Linux kernel.

REQUIREMENTS:
1. Backup current kernel configuration
2. Check available disk space
3. Update bootloader configuration
4. Preserve current kernel as fallback
5. Clear instructions for testing
6. Reboot planning
7. Rollback procedure

FORMAT YOUR RESPONSE AS:
```bash
# KERNEL UPDATE SCRIPT
<your kernel update script>
```

```bash
# ROLLBACK SCRIPT
<script to revert to previous kernel>
```

IMPORTANT: Include warnings about reboot requirement and testing procedures."""

    def _get_default_prompt(self) -> str:
        """Default system prompt"""
        return """You are a Linux system administrator and security expert. Generate safe remediation procedures.

Create a step-by-step remediation procedure for the vulnerability.

REQUIREMENTS:
1. Clear, actionable steps
2. Error handling and validation
3. Backup procedures
4. Testing instructions
5. Rollback capability

FORMAT YOUR RESPONSE AS:
```bash
# REMEDIATION SCRIPT
<your remediation script or procedure>
```

```bash
# ROLLBACK SCRIPT
<rollback procedure>
```"""

    def _build_user_prompt(
        self,
        vulnerability: Vulnerability,
        analysis: AnalysisResult
    ) -> str:
        """Build user prompt with vulnerability details"""
        prompt = f"""Generate a remediation script for the following vulnerability:

**CVE ID:** {vulnerability.cve_id}
**Title:** {vulnerability.title}
**Severity:** {vulnerability.severity.value if vulnerability.severity else 'Unknown'}
**CVSS Score:** {vulnerability.cvss_score or 'N/A'}

**Description:**
{vulnerability.description or 'No description available'}

**Affected Package:** {analysis.affected_package or 'Unknown'}
**Affected Version:** {analysis.affected_version or 'Unknown'}
**Fixed Version:** {analysis.fixed_version or 'Unknown'}

**Patch Type:** {analysis.patch_type.value}
**Package Manager:** {analysis.package_manager.value}
**Complexity:** {analysis.complexity}
**Requires Reboot:** {'Yes' if analysis.requires_reboot else 'No'}

**Recommendations:**
{chr(10).join(f'- {rec}' for rec in analysis.recommendations)}

Generate a complete, production-ready remediation script with error handling and rollback capability."""

        return prompt

    def _parse_llm_response(self, content: str) -> tuple[str, str]:
        """Parse LLM response to extract patch and rollback scripts"""
        import re

        # Extract patch script
        patch_match = re.search(
            r'```bash\s*\n#\s*(PATCH|REMEDIATION|WORKAROUND|KERNEL UPDATE).*?\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )

        # Extract rollback script
        rollback_match = re.search(
            r'```bash\s*\n#\s*(ROLLBACK|REMOVAL).*?\n(.*?)\n```',
            content,
            re.DOTALL | re.IGNORECASE
        )

        patch_content = patch_match.group(2).strip() if patch_match else content
        rollback_content = rollback_match.group(2).strip() if rollback_match else ""

        return patch_content, rollback_content

    def _calculate_confidence(
        self,
        analysis: AnalysisResult,
        llm_response: Any,
        patch_content: str
    ) -> float:
        """Calculate confidence score for generated patch"""
        confidence = analysis.confidence * 0.5  # Start with analysis confidence

        # Check patch quality indicators
        quality_indicators = [
            "set -e" in patch_content,  # Error handling
            "set -u" in patch_content,  # Undefined variable check
            "backup" in patch_content.lower(),  # Backup mentioned
            "#!/bin/bash" in patch_content,  # Proper shebang
            len(patch_content) > 100,  # Substantive script
        ]

        confidence += sum(quality_indicators) * 0.1

        return min(1.0, confidence)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if hasattr(self.llm_client, '__aexit__'):
            await self.llm_client.__aexit__(exc_type, exc_val, exc_tb)
