"""Patch validation and safety checking."""
import json
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a patch."""

    severity: str  # critical, high, medium, low
    description: str
    line_number: Optional[int] = None


@dataclass
class ValidationResult:
    """Result of patch validation."""

    is_valid: bool
    safety_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue]
    dangerous_commands: List[str]
    syntax_valid: bool
    recommendations: List[str]


class PatchValidator:
    """Validates generated patches for safety and correctness."""

    # Dangerous commands that should never appear
    FORBIDDEN_COMMANDS = [
        r"rm\s+-rf\s+/[^/]",  # rm -rf on root directories
        r"dd\s+if=",  # Disk operations
        r"mkfs",  # Filesystem creation
        r"fdisk",  # Disk partitioning
        r">/dev/sd[a-z]",  # Writing directly to disks
        r"chmod\s+777",  # Overly permissive permissions
        r"chown.*root",  # Changing ownership to root
        r":(){:\|:&};:",  # Fork bomb
        r"curl.*\|.*bash",  # Piping curl to bash (security risk)
        r"wget.*\|.*sh",  # Piping wget to shell
    ]

    # Suspicious patterns that warrant warnings
    SUSPICIOUS_PATTERNS = [
        r"rm\s+-rf",  # Recursive force delete
        r"chmod\s+[0-7]{3}",  # Permission changes
        r">/etc/",  # Writing to /etc
        r"systemctl\s+disable",  # Disabling services
        r"sed\s+-i",  # In-place file editing
        r"iptables.*FLUSH",  # Flushing firewall rules
        r"setenforce\s+0",  # Disabling SELinux
    ]

    # Required safety features
    REQUIRED_PATTERNS = [
        r"#!/bin/bash",  # Shebang
        r"set\s+-e",  # Exit on error (optional but recommended)
    ]

    def validate_syntax(self, script: str) -> tuple[bool, Optional[str]]:
        """
        Validate bash script syntax using bash -n.

        Args:
            script: Bash script content

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            result = subprocess.run(
                ["bash", "-n"],
                input=script.encode(),
                capture_output=True,
                timeout=5,
            )

            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr.decode()

        except subprocess.TimeoutExpired:
            return False, "Syntax check timed out"
        except Exception as e:
            return False, f"Syntax check failed: {e}"

    def check_shellcheck(self, script: str) -> tuple[bool, List[str]]:
        """
        Run shellcheck on the script if available.

        Args:
            script: Bash script content

        Returns:
            Tuple of (passed, issues_list)
        """
        try:
            result = subprocess.run(
                ["shellcheck", "-f", "json", "-"],
                input=script.encode(),
                capture_output=True,
                timeout=10,
            )

            if result.returncode == 0:
                return True, []

            # Parse shellcheck JSON output
            issues = json.loads(result.stdout.decode())
            issue_descriptions = [
                f"Line {issue['line']}: {issue['message']}" for issue in issues
            ]

            return False, issue_descriptions

        except FileNotFoundError:
            # Shellcheck not installed
            return True, ["Shellcheck not available - skipping"]
        except subprocess.TimeoutExpired:
            return False, ["Shellcheck timed out"]
        except Exception as e:
            return False, [f"Shellcheck error: {e}"]

    def detect_dangerous_commands(self, script: str) -> List[ValidationIssue]:
        """
        Detect dangerous commands in the script.

        Args:
            script: Bash script content

        Returns:
            List of validation issues
        """
        issues = []

        for pattern in self.FORBIDDEN_COMMANDS:
            matches = re.finditer(pattern, script, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # Find line number
                line_num = script[: match.start()].count("\n") + 1
                issues.append(
                    ValidationIssue(
                        severity="critical",
                        description=f"Forbidden command detected: {match.group()}",
                        line_number=line_num,
                    )
                )

        return issues

    def detect_suspicious_patterns(self, script: str) -> List[ValidationIssue]:
        """
        Detect suspicious patterns that may be risky.

        Args:
            script: Bash script content

        Returns:
            List of validation issues
        """
        issues = []

        for pattern in self.SUSPICIOUS_PATTERNS:
            matches = re.finditer(pattern, script, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                line_num = script[: match.start()].count("\n") + 1
                issues.append(
                    ValidationIssue(
                        severity="high",
                        description=f"Suspicious pattern detected: {match.group()}",
                        line_number=line_num,
                    )
                )

        return issues

    def check_required_features(self, script: str) -> List[ValidationIssue]:
        """
        Check for required safety features.

        Args:
            script: Bash script content

        Returns:
            List of validation issues for missing features
        """
        issues = []

        if not script.strip().startswith("#!/bin/bash"):
            issues.append(
                ValidationIssue(
                    severity="medium",
                    description="Missing shebang (#!/bin/bash)",
                    line_number=1,
                )
            )

        # Check for error handling
        if "set -e" not in script and "|| exit" not in script:
            issues.append(
                ValidationIssue(
                    severity="medium",
                    description="No error handling detected (consider 'set -e')",
                )
            )

        # Check for logging
        if "/var/log" not in script and "logger" not in script:
            issues.append(
                ValidationIssue(
                    severity="low",
                    description="No logging detected",
                )
            )

        # Check for idempotency
        if "if [" not in script and "[ -f" not in script:
            issues.append(
                ValidationIssue(
                    severity="medium",
                    description="Script may not be idempotent (no condition checks)",
                )
            )

        return issues

    def calculate_safety_score(
        self, issues: List[ValidationIssue], dangerous_commands: List[str]
    ) -> float:
        """
        Calculate overall safety score.

        Args:
            issues: List of validation issues
            dangerous_commands: List of dangerous commands found

        Returns:
            Safety score from 0.0 to 1.0
        """
        # Start with perfect score
        score = 1.0

        # Forbidden commands are disqualifying
        if dangerous_commands:
            return 0.0

        # Deduct points based on issue severity
        severity_weights = {"critical": 0.5, "high": 0.2, "medium": 0.1, "low": 0.05}

        for issue in issues:
            score -= severity_weights.get(issue.severity, 0.05)

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))

    def validate(self, script: str) -> ValidationResult:
        """
        Perform comprehensive validation of a patch script.

        Args:
            script: Bash script content to validate

        Returns:
            ValidationResult with detailed findings
        """
        issues: List[ValidationIssue] = []
        recommendations: List[str] = []

        # 1. Syntax validation
        syntax_valid, syntax_error = self.validate_syntax(script)
        if not syntax_valid:
            issues.append(
                ValidationIssue(severity="critical", description=f"Syntax error: {syntax_error}")
            )

        # 2. Detect dangerous commands
        dangerous_issues = self.detect_dangerous_commands(script)
        issues.extend(dangerous_issues)
        dangerous_commands = [issue.description for issue in dangerous_issues]

        # 3. Detect suspicious patterns
        suspicious_issues = self.detect_suspicious_patterns(script)
        issues.extend(suspicious_issues)

        # 4. Check required features
        required_issues = self.check_required_features(script)
        issues.extend(required_issues)

        # 5. Run shellcheck
        shellcheck_passed, shellcheck_issues = self.check_shellcheck(script)
        if not shellcheck_passed:
            for issue_desc in shellcheck_issues[:5]:  # Limit to first 5
                issues.append(ValidationIssue(severity="low", description=issue_desc))

        # 6. Generate recommendations
        if not syntax_valid:
            recommendations.append("Fix syntax errors before deployment")
        if dangerous_commands:
            recommendations.append("Remove dangerous commands immediately")
        if any(i.severity == "high" for i in issues):
            recommendations.append("Review and justify high-severity patterns")
        if not shellcheck_passed:
            recommendations.append("Address shellcheck warnings for best practices")

        recommendations.append("Test in isolated environment before production")
        recommendations.append("Review with security team before deployment")

        # 7. Calculate safety score
        safety_score = self.calculate_safety_score(issues, dangerous_commands)

        # 8. Determine if valid
        is_valid = syntax_valid and len(dangerous_commands) == 0 and safety_score >= 0.6

        return ValidationResult(
            is_valid=is_valid,
            safety_score=safety_score,
            issues=issues,
            dangerous_commands=dangerous_commands,
            syntax_valid=syntax_valid,
            recommendations=recommendations,
        )
