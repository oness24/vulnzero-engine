"""
LLM client for generating remediation patches
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from shared.config import settings

logger = structlog.get_logger()


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    async def generate_patch(
        self,
        vulnerability: Dict[str, Any],
        system_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a remediation patch

        Args:
            vulnerability: Vulnerability details
            system_context: System and package information

        Returns:
            Dictionary with patch details
        """
        pass

    @abstractmethod
    async def validate_patch(
        self,
        patch_script: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate a patch for safety and correctness

        Args:
            patch_script: The patch script to validate
            context: Context about the system

        Returns:
            Validation results
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI-based patch generation"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def generate_patch(
        self,
        vulnerability: Dict[str, Any],
        system_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate patch using OpenAI"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        prompt = self._build_patch_prompt(vulnerability, system_context)

        logger.info(
            "generating_patch_openai",
            cve_id=vulnerability.get("cve_id"),
            model=self.model,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cybersecurity expert specializing in vulnerability remediation. "
                            "Generate safe, production-ready remediation scripts. "
                            "Always include rollback steps and validation checks."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more deterministic output
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            parsed_result = self._parse_llm_response(content)

            logger.info(
                "patch_generated_openai",
                cve_id=vulnerability.get("cve_id"),
                confidence=parsed_result.get("confidence_score"),
            )

            return parsed_result

        except Exception as e:
            logger.error(
                "patch_generation_failed_openai",
                error=str(e),
                cve_id=vulnerability.get("cve_id"),
            )
            raise

    async def validate_patch(
        self,
        patch_script: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate patch using OpenAI"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        prompt = f"""
Analyze the following remediation script for security and safety issues:

```bash
{patch_script}
```

System Context:
- OS: {context.get('os_type')}
- Package Manager: {context.get('package_manager')}
- Critical System: {context.get('is_critical', False)}

Evaluate:
1. Safety: Does it avoid destructive operations?
2. Idempotency: Can it be run multiple times safely?
3. Rollback: Are rollback steps included?
4. Error Handling: Does it handle failures gracefully?
5. Privilege: Does it use minimal required privileges?

Provide a JSON response with:
- is_safe: boolean
- risk_level: "low", "medium", "high"
- issues: list of potential issues
- recommendations: list of improvements
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security auditor reviewing remediation scripts.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1000,
            )

            content = response.choices[0].message.content
            return self._parse_validation_response(content)

        except Exception as e:
            logger.error("patch_validation_failed", error=str(e))
            raise

    def _build_patch_prompt(
        self,
        vulnerability: Dict[str, Any],
        system_context: Dict[str, Any],
    ) -> str:
        """Build the patch generation prompt"""
        return f"""
Generate a remediation script for the following vulnerability:

CVE ID: {vulnerability.get('cve_id', 'N/A')}
Title: {vulnerability.get('title', 'N/A')}
Severity: {vulnerability.get('severity', 'N/A')}
CVSS Score: {vulnerability.get('cvss_score', 'N/A')}
Description: {vulnerability.get('description', 'N/A')}

Affected Package: {vulnerability.get('affected_package', 'N/A')}
Current Version: {vulnerability.get('current_version', 'N/A')}
Fixed Version: {vulnerability.get('fixed_version', 'N/A')}

System Context:
- OS Type: {system_context.get('os_type', 'linux')}
- OS Version: {system_context.get('os_version', 'N/A')}
- Package Manager: {system_context.get('package_manager', 'apt')}
- Asset Criticality: {system_context.get('asset_criticality', 5)}/10
- Production System: {system_context.get('is_production', False)}

Requirements:
1. Generate a bash script that remediates this vulnerability
2. Use the appropriate package manager ({system_context.get('package_manager', 'apt')})
3. Include pre-flight checks (current version verification)
4. Include rollback script as a separate section
5. Add validation steps to verify the fix
6. Use error handling (set -e, trap)
7. Make it idempotent (can run multiple times safely)
8. Include comments explaining each step
9. Avoid any destructive operations beyond patching
10. Consider minimal downtime for production systems

Provide your response in the following JSON format:
{{
  "patch_script": "the main remediation script",
  "rollback_script": "script to revert changes",
  "validation_script": "script to verify the fix worked",
  "confidence_score": <0-100>,
  "estimated_duration_minutes": <number>,
  "requires_restart": <boolean>,
  "risk_assessment": "low|medium|high",
  "prerequisites": ["list", "of", "prerequisites"],
  "affected_services": ["services", "that", "need", "restart"],
  "notes": "additional notes or warnings"
}}
"""

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        import json
        import re

        # Try to extract JSON from the response
        # LLMs sometimes wrap JSON in markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                logger.warning("failed_to_parse_json_from_llm", content=content[:200])
                # Return a fallback response
                return {
                    "patch_script": content,
                    "rollback_script": "",
                    "validation_script": "",
                    "confidence_score": 50,
                    "estimated_duration_minutes": 5,
                    "requires_restart": False,
                    "risk_assessment": "medium",
                    "prerequisites": [],
                    "affected_services": [],
                    "notes": "Failed to parse structured response",
                }

        try:
            result = json.loads(json_str)
            # Ensure all required fields are present
            defaults = {
                "patch_script": "",
                "rollback_script": "",
                "validation_script": "",
                "confidence_score": 50,
                "estimated_duration_minutes": 5,
                "requires_restart": False,
                "risk_assessment": "medium",
                "prerequisites": [],
                "affected_services": [],
                "notes": "",
            }
            defaults.update(result)
            return defaults
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), content=json_str[:200])
            raise

    def _parse_validation_response(self, content: str) -> Dict[str, Any]:
        """Parse validation response"""
        import json
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Fallback
                return {
                    "is_safe": True,
                    "risk_level": "medium",
                    "issues": [],
                    "recommendations": [],
                }

        try:
            result = json.loads(json_str)
            defaults = {
                "is_safe": True,
                "risk_level": "medium",
                "issues": [],
                "recommendations": [],
            }
            defaults.update(result)
            return defaults
        except json.JSONDecodeError:
            return {
                "is_safe": True,
                "risk_level": "medium",
                "issues": [],
                "recommendations": [],
            }


class AnthropicClient(LLMClient):
    """Anthropic Claude-based patch generation"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self.client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None

    async def generate_patch(
        self,
        vulnerability: Dict[str, Any],
        system_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate patch using Anthropic Claude"""
        if not self.client:
            raise ValueError("Anthropic API key not configured")

        prompt = self._build_patch_prompt(vulnerability, system_context)

        logger.info(
            "generating_patch_anthropic",
            cve_id=vulnerability.get("cve_id"),
            model=self.model,
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system=(
                    "You are a cybersecurity expert specializing in vulnerability remediation. "
                    "Generate safe, production-ready remediation scripts. "
                    "Always include rollback steps and validation checks."
                ),
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            parsed_result = self._parse_llm_response(content)

            logger.info(
                "patch_generated_anthropic",
                cve_id=vulnerability.get("cve_id"),
                confidence=parsed_result.get("confidence_score"),
            )

            return parsed_result

        except Exception as e:
            logger.error(
                "patch_generation_failed_anthropic",
                error=str(e),
                cve_id=vulnerability.get("cve_id"),
            )
            raise

    async def validate_patch(
        self,
        patch_script: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate patch using Anthropic Claude"""
        if not self.client:
            raise ValueError("Anthropic API key not configured")

        prompt = f"""
Analyze the following remediation script for security and safety issues:

```bash
{patch_script}
```

System Context:
- OS: {context.get('os_type')}
- Package Manager: {context.get('package_manager')}
- Critical System: {context.get('is_critical', False)}

Evaluate:
1. Safety: Does it avoid destructive operations?
2. Idempotency: Can it be run multiple times safely?
3. Rollback: Are rollback steps included?
4. Error Handling: Does it handle failures gracefully?
5. Privilege: Does it use minimal required privileges?

Provide a JSON response with:
- is_safe: boolean
- risk_level: "low", "medium", "high"
- issues: list of potential issues
- recommendations: list of improvements
"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.2,
                system="You are a security auditor reviewing remediation scripts.",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            return self._parse_validation_response(content)

        except Exception as e:
            logger.error("patch_validation_failed", error=str(e))
            raise

    # Reuse the same prompt building and parsing methods from OpenAI client
    _build_patch_prompt = OpenAIClient._build_patch_prompt
    _parse_llm_response = OpenAIClient._parse_llm_response
    _parse_validation_response = OpenAIClient._parse_validation_response


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    Factory function to get appropriate LLM client

    Args:
        provider: "openai" or "anthropic", defaults to settings

    Returns:
        LLMClient instance
    """
    provider = provider or settings.llm_provider

    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
