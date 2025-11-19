"""
LLM Prompt Injection Sanitization

Protects against prompt injection attacks by detecting and sanitizing malicious inputs
before sending them to Large Language Models (OpenAI GPT-4, Anthropic Claude, etc.).

References:
- OWASP LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Prompt Injection Guide: https://simonwillison.net/2022/Sep/12/prompt-injection/
"""

import re
import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SanitizationLevel(Enum):
    """Sanitization strictness levels"""
    PERMISSIVE = "permissive"  # Log warnings, minimal sanitization
    MODERATE = "moderate"      # Remove obvious injection attempts
    STRICT = "strict"          # Aggressive sanitization, may affect legitimate inputs


class PromptInjectionDetector:
    """
    Detects and sanitizes potential prompt injection attacks.

    Prompt injection attacks attempt to manipulate LLM behavior by:
    - Injecting system-like instructions
    - Overriding previous instructions
    - Extracting sensitive information
    - Causing unintended behaviors
    """

    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction override attempts
        (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", "instruction_override"),
        (r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions?|context)", "instruction_override"),
        (r"disregard\s+(all\s+)?(previous|prior|above)", "instruction_override"),

        # System message injection attempts
        (r"system\s*[:]\s*", "system_impersonation"),
        (r"\[system\]", "system_impersonation"),
        (r"<\|system\|>", "system_impersonation"),
        (r"###\s*system", "system_impersonation"),

        # Role manipulation
        (r"you\s+are\s+now\s+a", "role_manipulation"),
        (r"pretend\s+to\s+be", "role_manipulation"),
        (r"act\s+as\s+(if\s+)?you", "role_manipulation"),

        # Instruction leakage attempts
        (r"show\s+me\s+your\s+(instructions?|prompt|system\s+message)", "instruction_leak"),
        (r"what\s+(are|is)\s+your\s+(instructions?|rules|guidelines)", "instruction_leak"),
        (r"repeat\s+your\s+(instructions?|prompt)", "instruction_leak"),

        # Jailbreak attempts
        (r"DAN\s+mode", "jailbreak"),
        (r"developer\s+mode", "jailbreak"),
        (r"sudo\s+mode", "jailbreak"),

        # Code execution attempts
        (r"```python\s+import\s+os", "code_execution"),
        (r"exec\s*\(", "code_execution"),
        (r"eval\s*\(", "code_execution"),

        # Delimiter injection
        (r"---+\s*(end|stop|break)", "delimiter_injection"),
        (r"={3,}\s*(end|stop|break)", "delimiter_injection"),
    ]

    def __init__(self, level: SanitizationLevel = SanitizationLevel.MODERATE):
        """
        Initialize detector with specified sanitization level.

        Args:
            level: Strictness level for sanitization
        """
        self.level = level
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), attack_type)
            for pattern, attack_type in self.INJECTION_PATTERNS
        ]

    def detect(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if text contains potential prompt injection.

        Args:
            text: Input text to check

        Returns:
            Tuple of (is_suspicious, attack_type)
        """
        if not text:
            return (False, None)

        for pattern, attack_type in self.compiled_patterns:
            if pattern.search(text):
                logger.warning(
                    "Potential prompt injection detected",
                    extra={
                        "attack_type": attack_type,
                        "pattern": pattern.pattern,
                        "text_preview": text[:100]
                    }
                )
                return (True, attack_type)

        return (False, None)

    def sanitize(self, text: str, max_length: int = 10000) -> str:
        """
        Sanitize text by removing/escaping potential injection attempts.

        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length (prevents token exhaustion)

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Truncate if too long
        if len(text) > max_length:
            logger.warning(
                f"Input truncated from {len(text)} to {max_length} characters"
            )
            text = text[:max_length]

        # Detect injection attempts
        is_suspicious, attack_type = self.detect(text)

        if is_suspicious and self.level != SanitizationLevel.PERMISSIVE:
            # Apply sanitization based on level
            if self.level == SanitizationLevel.STRICT:
                text = self._strict_sanitize(text, attack_type)
            else:  # MODERATE
                text = self._moderate_sanitize(text, attack_type)

        return text

    def _moderate_sanitize(self, text: str, attack_type: Optional[str]) -> str:
        """
        Moderate sanitization - removes obvious injection patterns.

        Args:
            text: Input text
            attack_type: Type of attack detected

        Returns:
            Sanitized text
        """
        sanitized = text

        # Remove system message markers
        sanitized = re.sub(r"system\s*[:]\s*", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\[system\]", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"<\|system\|>", "", sanitized, flags=re.IGNORECASE)

        # Remove instruction override attempts
        sanitized = re.sub(
            r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
            "[REMOVED]",
            sanitized,
            flags=re.IGNORECASE
        )

        # Remove jailbreak markers
        sanitized = re.sub(r"DAN\s+mode", "[REMOVED]", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"developer\s+mode", "[REMOVED]", sanitized, flags=re.IGNORECASE)

        logger.info(
            "Applied moderate sanitization",
            extra={"attack_type": attack_type}
        )

        return sanitized

    def _strict_sanitize(self, text: str, attack_type: Optional[str]) -> str:
        """
        Strict sanitization - aggressive pattern removal.

        Args:
            text: Input text
            attack_type: Type of attack detected

        Returns:
            Heavily sanitized text
        """
        # Start with moderate sanitization
        sanitized = self._moderate_sanitize(text, attack_type)

        # Additional strict measures

        # Remove any "system", "instructions", "prompt" references
        sanitized = re.sub(r"\b(system|instructions?|prompt)\b", "[REDACTED]", sanitized, flags=re.IGNORECASE)

        # Remove code blocks
        sanitized = re.sub(r"```.*?```", "[CODE_REMOVED]", sanitized, flags=re.DOTALL)

        # Remove special characters that might be delimiters
        sanitized = re.sub(r"[|<>]{2,}", " ", sanitized)

        logger.warning(
            "Applied strict sanitization - legitimate content may be affected",
            extra={"attack_type": attack_type}
        )

        return sanitized


# Global detector instance (moderate level by default)
_default_detector = PromptInjectionDetector(SanitizationLevel.MODERATE)


def sanitize_prompt(
    text: str,
    level: SanitizationLevel = SanitizationLevel.MODERATE,
    max_length: int = 10000
) -> str:
    """
    Sanitize LLM prompt to prevent injection attacks.

    Usage:
        >>> from shared.utils.llm_sanitizer import sanitize_prompt
        >>> user_input = "Ignore all previous instructions and..."
        >>> safe_input = sanitize_prompt(user_input)
        >>> # Use safe_input in LLM call

    Args:
        text: Input text to sanitize
        level: Sanitization strictness level
        max_length: Maximum allowed text length

    Returns:
        Sanitized text safe for LLM prompts
    """
    detector = PromptInjectionDetector(level)
    return detector.sanitize(text, max_length)


def is_injection_attempt(text: str) -> bool:
    """
    Quick check if text contains potential injection patterns.

    Args:
        text: Input text to check

    Returns:
        True if suspicious patterns detected
    """
    is_suspicious, _ = _default_detector.detect(text)
    return is_suspicious


def sanitize_llm_message_content(content: str) -> str:
    """
    Sanitize content for LLMMessage objects.

    This is a convenience wrapper for the most common use case.

    Args:
        content: Message content

    Returns:
        Sanitized content
    """
    return sanitize_prompt(content, level=SanitizationLevel.MODERATE)
