"""
Patch validation and safety checks
"""

from typing import Dict, Any, List
import re
import structlog

logger = structlog.get_logger()


class PatchValidator:
    """Validates patches for safety and correctness"""

    # Dangerous commands that should never appear in patches
    DANGEROUS_COMMANDS = [
        r"\brm\s+-rf\s+/",  # rm -rf /
        r"\bdd\s+if=/dev/zero",  # Disk wipe
        r"\bmkfs\.",  # Format filesystem
        r"\bformat\b",  # Format command
        r"\b:\(\)\{:\|\:&\};:",  # Fork bomb
        r"\b>/dev/sd[a-z]",  # Direct disk write
        r"\bshred\b",  # Secure delete
        r"\bcryptsetup\b",  # Disk encryption operations
    ]

    # Commands that are risky but may be acceptable with proper context
    RISKY_COMMANDS = [
        r"\brm\s+-rf",  # Recursive force remove
        r"\bchmod\s+777",  # Overly permissive permissions
        r"\bsystemctl\s+stop",  # Service stop (may be needed)
        r"\bkillall",  # Kill processes
        r"\breboot",  # System reboot
        r"\bshutdown",  # System shutdown
        r"\biptables\s+-F",  # Flush firewall rules
        r"\buseradd.*-u\s+0",  # Create root user
        r"\bwget.*\|\s*bash",  # Pipe to bash
        r"\bcurl.*\|\s*bash",  # Pipe to bash
    ]

    # Required security patterns
    RECOMMENDED_PATTERNS = [
        r"set -e",  # Exit on error
        r"set -u",  # Exit on undefined variable
        r"\[\s*\"\$EUID\"\s*-ne\s*0\s*\]",  # Root check
    ]

    def __init__(self):
        self.dangerous_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_COMMANDS]
        self.risky_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.RISKY_COMMANDS]
        self.recommended_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.RECOMMENDED_PATTERNS]

    def validate_patch(self, patch_script: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate a patch script for safety and best practices

        Args:
            patch_script: The bash script to validate
            context: Optional context about the system

        Returns:
            Dictionary with validation results
        """
        context = context or {}
        issues = []
        warnings = []
        recommendations = []

        # Check for dangerous commands
        dangerous_found = self._check_dangerous_commands(patch_script)
        if dangerous_found:
            issues.extend(dangerous_found)

        # Check for risky commands
        risky_found = self._check_risky_commands(patch_script)
        if risky_found:
            warnings.extend(risky_found)

        # Check for recommended patterns
        missing_recommendations = self._check_recommended_patterns(patch_script)
        if missing_recommendations:
            recommendations.extend(missing_recommendations)

        # Check for common issues
        common_issues = self._check_common_issues(patch_script)
        warnings.extend(common_issues)

        # Check idempotency
        if not self._check_idempotency(patch_script):
            warnings.append(
                "Script may not be idempotent - consider adding checks to prevent errors on re-run"
            )

        # Determine overall safety
        is_safe = len(issues) == 0
        risk_level = self._calculate_risk_level(issues, warnings, context)

        result = {
            "is_safe": is_safe,
            "risk_level": risk_level,
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "score": self._calculate_safety_score(issues, warnings, recommendations),
        }

        logger.info(
            "patch_validated",
            is_safe=is_safe,
            risk_level=risk_level,
            issues_count=len(issues),
            warnings_count=len(warnings),
        )

        return result

    def _check_dangerous_commands(self, script: str) -> List[str]:
        """Check for dangerous commands"""
        found = []
        for regex in self.dangerous_regex:
            matches = regex.findall(script)
            if matches:
                found.append(f"CRITICAL: Dangerous command detected: {matches[0]}")
        return found

    def _check_risky_commands(self, script: str) -> List[str]:
        """Check for risky commands"""
        found = []
        for regex in self.risky_regex:
            matches = regex.findall(script)
            if matches:
                found.append(f"Risky command found: {matches[0]}")
        return found

    def _check_recommended_patterns(self, script: str) -> List[str]:
        """Check for recommended security patterns"""
        missing = []

        # Check for error handling
        if "set -e" not in script and "set -euo" not in script:
            missing.append("Missing error handling (set -e or set -euo pipefail)")

        # Check for undefined variable handling
        if "set -u" not in script and "set -euo" not in script:
            missing.append("Missing undefined variable handling (set -u)")

        # Check for root/privilege check
        if "EUID" not in script and "id -u" not in script:
            missing.append("Missing privilege check - should verify running as root")

        return missing

    def _check_common_issues(self, script: str) -> List[str]:
        """Check for common scripting issues"""
        issues = []

        # Check for unquoted variables
        unquoted_vars = re.findall(r'\$[A-Z_]+(?!["\'])', script)
        if unquoted_vars:
            issues.append(f"Unquoted variables found (may cause word splitting): {', '.join(set(unquoted_vars)[:3])}")

        # Check for missing shebang
        if not script.strip().startswith("#!"):
            issues.append("Missing shebang (#!/bin/bash)")

        # Check for hardcoded credentials
        if re.search(r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', script, re.IGNORECASE):
            issues.append("Potential hardcoded credentials detected")

        # Check for eval usage
        if re.search(r'\beval\b', script):
            issues.append("Use of 'eval' detected - can be dangerous")

        # Check for sudo without specific commands
        if re.search(r'\bsudo\s+bash\b|\bsudo\s+sh\b', script):
            issues.append("Overly permissive sudo usage detected")

        return issues

    def _check_idempotency(self, script: str) -> bool:
        """Check if script appears to be idempotent"""
        # Look for idempotency indicators
        idempotency_patterns = [
            r"if\s+\[.*\].*then",  # Conditional checks
            r"test\s+-[ef]",  # File existence checks
            r"which\b",  # Command existence checks
            r"command\s+-v",  # Command availability checks
            r"\|\|\s*echo",  # Error handling with fallback
        ]

        for pattern in idempotency_patterns:
            if re.search(pattern, script):
                return True

        return False

    def _calculate_risk_level(
        self,
        issues: List[str],
        warnings: List[str],
        context: Dict[str, Any],
    ) -> str:
        """Calculate overall risk level"""
        if issues:
            return "critical"

        is_production = context.get("is_production", False)
        is_critical = context.get("is_critical", False)

        if is_production or is_critical:
            if len(warnings) >= 3:
                return "high"
            elif len(warnings) >= 1:
                return "medium"
            else:
                return "low"
        else:
            if len(warnings) >= 5:
                return "high"
            elif len(warnings) >= 3:
                return "medium"
            else:
                return "low"

    def _calculate_safety_score(
        self,
        issues: List[str],
        warnings: List[str],
        recommendations: List[str],
    ) -> float:
        """
        Calculate a safety score (0-100)

        Higher is safer
        """
        score = 100.0

        # Critical issues
        score -= len(issues) * 50

        # Warnings
        score -= len(warnings) * 10

        # Missing recommendations
        score -= len(recommendations) * 5

        return max(0.0, min(100.0, score))

    def validate_rollback_script(self, rollback_script: str) -> Dict[str, Any]:
        """
        Validate a rollback script

        Rollback scripts have similar requirements but are even more critical
        """
        result = self.validate_patch(rollback_script)

        # Additional checks for rollback scripts
        additional_issues = []

        # Rollback should have version verification
        if "version" not in rollback_script.lower():
            additional_issues.append("Rollback script should verify version after downgrade")

        # Should have success confirmation
        if "success" not in rollback_script.lower() and "complete" not in rollback_script.lower():
            additional_issues.append("Rollback script should confirm successful completion")

        if additional_issues:
            result["warnings"].extend(additional_issues)
            result["score"] = self._calculate_safety_score(
                result["issues"],
                result["warnings"],
                result["recommendations"],
            )

        return result


class PatchAnalyzer:
    """Analyzes patches to extract metadata and estimate impact"""

    def analyze_patch(self, patch_script: str) -> Dict[str, Any]:
        """
        Analyze a patch script to extract metadata

        Args:
            patch_script: The patch script to analyze

        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "requires_restart": self._check_restart_required(patch_script),
            "affected_services": self._extract_affected_services(patch_script),
            "estimated_duration": self._estimate_duration(patch_script),
            "network_required": self._check_network_required(patch_script),
            "disk_operations": self._check_disk_operations(patch_script),
            "privilege_required": "root" if self._requires_root(patch_script) else "user",
        }

        logger.debug("patch_analyzed", **analysis)

        return analysis

    def _check_restart_required(self, script: str) -> bool:
        """Check if script requires system restart"""
        restart_indicators = [
            r"\breboot\b",
            r"\bshutdown\s+-r",
            r"\bsystemctl\s+reboot",
            r"kernel",  # Kernel updates usually need restart
            r"init\.d.*restart",
        ]

        for pattern in restart_indicators:
            if re.search(pattern, script, re.IGNORECASE):
                return True

        return False

    def _extract_affected_services(self, script: str) -> List[str]:
        """Extract list of services that will be affected"""
        services = []

        # Look for systemctl operations
        systemctl_matches = re.findall(
            r"systemctl\s+(?:restart|stop|reload)\s+([a-zA-Z0-9_.-]+)",
            script,
        )
        services.extend(systemctl_matches)

        # Look for service operations
        service_matches = re.findall(r"service\s+([a-zA-Z0-9_.-]+)\s+(?:restart|stop|reload)", script)
        services.extend(service_matches)

        # Look for init.d scripts
        initd_matches = re.findall(r"/etc/init\.d/([a-zA-Z0-9_.-]+)\s+(?:restart|stop|reload)", script)
        services.extend(initd_matches)

        return list(set(services))

    def _estimate_duration(self, script: str) -> int:
        """Estimate execution duration in minutes"""
        # Base duration
        duration = 2

        # Add time for package operations
        if re.search(r"apt-get\s+update", script):
            duration += 2
        if re.search(r"apt-get\s+install|apt-get\s+upgrade", script):
            duration += 3
        if re.search(r"yum\s+update|dnf\s+update", script):
            duration += 3

        # Add time for service restarts
        service_count = len(self._extract_affected_services(script))
        duration += service_count * 1

        # Add time if reboot required
        if self._check_restart_required(script):
            duration += 5

        return duration

    def _check_network_required(self, script: str) -> bool:
        """Check if network access is required"""
        network_indicators = [
            r"apt-get\s+update",
            r"yum\s+update",
            r"dnf\s+update",
            r"zypper\s+refresh",
            r"wget\b",
            r"curl\b",
            r"git\s+clone",
        ]

        for pattern in network_indicators:
            if re.search(pattern, script, re.IGNORECASE):
                return True

        return False

    def _check_disk_operations(self, script: str) -> bool:
        """Check if script performs significant disk operations"""
        disk_indicators = [
            r"\bmount\b",
            r"\bumount\b",
            r"\bmkdir\b",
            r"\brm\s+-rf",
            r"\bdd\b",
            r"\btar\s+",
            r"\bcp\s+-r",
        ]

        for pattern in disk_indicators:
            if re.search(pattern, script, re.IGNORECASE):
                return True

        return False

    def _requires_root(self, script: str) -> bool:
        """Check if script requires root privileges"""
        root_indicators = [
            r"\bsudo\b",
            r"apt-get",
            r"yum\b",
            r"dnf\b",
            r"zypper",
            r"systemctl",
            r"service\s+",
            r"/etc/",
            r"EUID.*0",
        ]

        for pattern in root_indicators:
            if re.search(pattern, script, re.IGNORECASE):
                return True

        return False
