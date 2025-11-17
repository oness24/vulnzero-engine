"""
Patch Validator

Validates generated patches for safety and correctness.
"""

from typing import List, Dict, Any
import re
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Result of patch validation"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    safety_score: float = 0.0  # 0.0-1.0
    issues: List[Dict[str, Any]] = []


class PatchValidator:
    """
    Validates generated patches for safety and correctness.
    """

    def __init__(self):
        """Initialize patch validator"""
        self.logger = logging.getLogger(__name__)

        # Dangerous commands that should not appear in patches
        self.dangerous_commands = [
            r'\brm\s+-rf\s+/',  # rm -rf /
            r'\bdd\s+if=',  # dd commands
            r':\(\)\{\s*:\|:\&\s*\};:',  # Fork bomb
            r'\bmkfs\.',  # Format filesystem
            r'\bfdisk\b',  # Partition manipulation
            r'>/dev/sd[a-z]',  # Direct disk writes
        ]

        # Suspicious patterns
        self.suspicious_patterns = [
            r'curl\s+.*\|\s*bash',  # Pipe to bash
            r'wget\s+.*\|\s*bash',
            r'eval\s+\$\(',  # eval with command substitution
            r'chmod\s+777',  # Overly permissive permissions
        ]

    def validate(self, patch_content: str) -> ValidationResult:
        """
        Validate a patch script.

        Args:
            patch_content: Generated patch script

        Returns:
            ValidationResult with validation status and issues
        """
        errors = []
        warnings = []
        issues = []

        # Check for dangerous commands
        for pattern in self.dangerous_commands:
            if re.search(pattern, patch_content, re.IGNORECASE):
                errors.append(f"Dangerous command pattern detected: {pattern}")
                issues.append({
                    "type": "error",
                    "category": "dangerous_command",
                    "pattern": pattern,
                })

        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, patch_content):
                warnings.append(f"Suspicious pattern detected: {pattern}")
                issues.append({
                    "type": "warning",
                    "category": "suspicious_pattern",
                    "pattern": pattern,
                })

        # Check for basic safety features
        safety_checks = {
            "has_shebang": r'^#!/bin/(ba)?sh',
            "has_error_handling": r'set\s+-e',
            "has_undefined_check": r'set\s+-u',
            "has_logging": r'(echo|log)',
            "has_backup": r'(backup|cp\s+.*\.bak)',
        }

        safety_score = 0.0
        for check_name, pattern in safety_checks.items():
            if re.search(pattern, patch_content, re.MULTILINE):
                safety_score += 0.2
            else:
                warnings.append(f"Missing recommended feature: {check_name}")

        # Check syntax (basic bash syntax)
        syntax_errors = self._check_bash_syntax(patch_content)
        if syntax_errors:
            errors.extend(syntax_errors)
            issues.extend([{
                "type": "error",
                "category": "syntax",
                "message": err
            } for err in syntax_errors])

        # Determine if valid
        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            safety_score=min(1.0, safety_score),
            issues=issues,
        )

        self.logger.info(
            f"Validation result: valid={is_valid}, "
            f"errors={len(errors)}, warnings={len(warnings)}, "
            f"safety_score={safety_score:.2f}"
        )

        return result

    def _check_bash_syntax(self, content: str) -> List[str]:
        """Basic bash syntax checking"""
        errors = []

        # Check for unclosed quotes
        single_quotes = content.count("'") - content.count("\\'")
        double_quotes = content.count('"') - content.count('\\"')

        if single_quotes % 2 != 0:
            errors.append("Unclosed single quote detected")

        if double_quotes % 2 != 0:
            errors.append("Unclosed double quote detected")

        # Check for unclosed command substitution
        if content.count('$(') != content.count(')'):
            errors.append("Unclosed command substitution")

        # Check for unclosed brace expansion
        if content.count('{') != content.count('}'):
            errors.append("Unclosed brace expansion")

        return errors


def validate_patch(patch_content: str) -> ValidationResult:
    """
    Convenience function to validate a patch.

    Args:
        patch_content: Patch script content

    Returns:
        ValidationResult
    """
    validator = PatchValidator()
    return validator.validate(patch_content)
