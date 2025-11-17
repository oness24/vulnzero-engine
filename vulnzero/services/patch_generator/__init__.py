"""Patch generator service for VulnZero."""
from .cve_fetcher import CVEData, CVEFetcher
from .generator import PatchGenerationResult, PatchGenerator
from .llm_client import AnthropicClient, LLMClient, OpenAIClient, get_llm_client
from .storage import PatchStorageService
from .templates import TemplateLibrary, template_library
from .validator import PatchValidator, ValidationResult

__all__ = [
    # Generator
    "PatchGenerator",
    "PatchGenerationResult",
    # LLM Clients
    "LLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "get_llm_client",
    # CVE Fetcher
    "CVEFetcher",
    "CVEData",
    # Validator
    "PatchValidator",
    "ValidationResult",
    # Templates
    "TemplateLibrary",
    "template_library",
    # Storage
    "PatchStorageService",
]
