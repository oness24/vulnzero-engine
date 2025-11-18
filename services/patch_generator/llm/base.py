"""
Base LLM Client Interface

Abstract base class for LLM integrations (OpenAI, Anthropic, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class LLMMessage(BaseModel):
    """Message in LLM conversation"""
    role: str  # system, user, assistant
    content: str


class LLMResponse(BaseModel):
    """Response from LLM"""
    content: str
    model: str
    tokens_used: int
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    All LLM integrations must implement this interface.
    """

    def __init__(self, api_key: str, model: str = None):
        """
        Initialize LLM client.

        Args:
            api_key: API key for the LLM provider
            model: Model identifier (provider-specific)
        """
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(f"llm.{self.__class__.__name__.lower()}")

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from LLM.

        Args:
            messages: Conversation messages
            temperature: Randomness (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific arguments

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def generate_with_retry(
        self,
        messages: List[LLMMessage],
        max_retries: int = 3,
        **kwargs
    ) -> LLMResponse:
        """
        Generate with automatic retry on failure.

        Args:
            messages: Conversation messages
            max_retries: Maximum number of retries
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse with generated content
        """
        pass

    def create_system_message(self, content: str) -> LLMMessage:
        """Create a system message"""
        return LLMMessage(role="system", content=content)

    def create_user_message(self, content: str) -> LLMMessage:
        """Create a user message"""
        return LLMMessage(role="user", content=content)

    def create_assistant_message(self, content: str) -> LLMMessage:
        """Create an assistant message"""
        return LLMMessage(role="assistant", content=content)


class LLMError(Exception):
    """Base exception for LLM errors"""
    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded"""
    pass


class LLMAuthenticationError(LLMError):
    """Authentication failed"""
    pass


class LLMTimeoutError(LLMError):
    """Request timed out"""
    pass
