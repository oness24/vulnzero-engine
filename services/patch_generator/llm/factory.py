"""
LLM Client Factory

Factory for creating LLM clients based on configuration.
"""

from typing import Optional
import logging

from services.patch_generator.llm.base import BaseLLMClient
from services.patch_generator.llm.openai_client import OpenAIClient
from services.patch_generator.llm.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM clients"""

    @staticmethod
    def create_client(
        provider: str,
        api_key: str,
        model: Optional[str] = None
    ) -> BaseLLMClient:
        """
        Create an LLM client based on provider.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            api_key: API key for the provider
            model: Optional specific model to use

        Returns:
            BaseLLMClient instance

        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()

        if provider == "openai":
            default_model = "gpt-4"
            client = OpenAIClient(
                api_key=api_key,
                model=model or default_model
            )
            logger.info(f"Created OpenAI client with model: {client.model}")
            return client

        elif provider == "anthropic":
            default_model = "claude-3-sonnet-20240229"
            client = AnthropicClient(
                api_key=api_key,
                model=model or default_model
            )
            logger.info(f"Created Anthropic client with model: {client.model}")
            return client

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Use 'openai' or 'anthropic'")

    @staticmethod
    def create_from_config(config: dict) -> BaseLLMClient:
        """
        Create client from configuration dictionary.

        Args:
            config: Configuration with 'provider', 'api_key', and optional 'model'

        Returns:
            BaseLLMClient instance
        """
        provider = config.get("provider")
        api_key = config.get("api_key")
        model = config.get("model")

        if not provider:
            raise ValueError("Configuration must include 'provider'")
        if not api_key:
            raise ValueError("Configuration must include 'api_key'")

        return LLMFactory.create_client(provider, api_key, model)


# Convenience function
def get_llm_client(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMClient:
    """
    Convenience function to get an LLM client.

    Args:
        provider: LLM provider name
        api_key: API key (if None, will try to load from environment)
        model: Model name

    Returns:
        BaseLLMClient instance
    """
    if not api_key:
        import os
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(f"No API key provided and no environment variable found for {provider}")

    return LLMFactory.create_client(provider, api_key, model)
