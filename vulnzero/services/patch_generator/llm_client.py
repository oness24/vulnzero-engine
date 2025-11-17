"""LLM client abstraction layer for patch generation."""
from abc import ABC, abstractmethod
from typing import Optional

from vulnzero.shared.config import get_settings

settings = get_settings()


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """
        Generate text completion from prompt.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client for patch generation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            model: Model name (uses settings if not provided)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
            )

        self.client = OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """Generate patch using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Linux system administrator and security engineer. "
                        "Generate safe, production-ready remediation scripts for vulnerabilities.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    def get_model_name(self) -> str:
        """Get the OpenAI model name."""
        return self.model


class AnthropicClient(LLMClient):
    """Anthropic Claude API client for patch generation."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (uses settings if not provided)
            model: Model name (uses settings if not provided)
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install anthropic"
            )

        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable."
            )

        self.client = Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """Generate patch using Anthropic Claude API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are an expert Linux system administrator and security engineer. "
                "Generate safe, production-ready remediation scripts for vulnerabilities.",
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text.strip()

        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")

    def get_model_name(self) -> str:
        """Get the Anthropic model name."""
        return self.model


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    Get LLM client based on configuration.

    Args:
        provider: LLM provider ('openai' or 'anthropic'). Uses settings if not provided.

    Returns:
        LLMClient instance

    Raises:
        ValueError: If provider is invalid or API key is missing
    """
    provider = provider or settings.llm_provider

    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    else:
        raise ValueError(
            f"Invalid LLM provider: {provider}. Must be 'openai' or 'anthropic'."
        )
