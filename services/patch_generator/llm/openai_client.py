"""
OpenAI LLM Client

Integration with OpenAI API (GPT-4, GPT-3.5-turbo)
"""

import asyncio
from typing import List
import httpx
import logging

from services.patch_generator.llm.base import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client for GPT models.

    Supported models:
    - gpt-4
    - gpt-4-turbo-preview
    - gpt-3.5-turbo
    """

    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4)
        """
        super().__init__(api_key, model)
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using OpenAI API.

        Args:
            messages: Conversation messages
            temperature: Randomness (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters

        Returns:
            LLMResponse with generated content
        """
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add optional parameters
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            if "frequency_penalty" in kwargs:
                payload["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                payload["presence_penalty"] = kwargs["presence_penalty"]

            # Make API request
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )

            # Handle errors
            if response.status_code == 401:
                raise LLMAuthenticationError("Invalid OpenAI API key")
            elif response.status_code == 429:
                raise LLMRateLimitError("OpenAI rate limit exceeded")
            elif response.status_code != 200:
                raise LLMError(f"OpenAI API error: {response.status_code} - {response.text}")

            # Parse response
            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"],
                model=data["model"],
                tokens_used=usage.get("total_tokens", 0),
                finish_reason=choice.get("finish_reason"),
                metadata={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                },
            )

        except httpx.TimeoutException:
            raise LLMTimeoutError("OpenAI API request timed out")
        except httpx.HTTPError as e:
            raise LLMError(f"OpenAI HTTP error: {e}")
        except Exception as e:
            raise LLMError(f"OpenAI error: {e}")

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
            **kwargs: Generation parameters

        Returns:
            LLMResponse with generated content
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self.generate(messages, **kwargs)

            except LLMRateLimitError as e:
                last_error = e
                wait_time = (2 ** attempt) * 5  # Exponential backoff: 5s, 10s, 20s
                self.logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)

            except LLMTimeoutError as e:
                last_error = e
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                self.logger.warning(f"Timeout, retrying after {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

            except LLMAuthenticationError:
                # Don't retry authentication errors
                raise

            except LLMError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Error: {e}, retrying after {wait_time}s")
                    await asyncio.sleep(wait_time)

        # All retries failed
        raise LLMError(f"Failed after {max_retries} retries. Last error: {last_error}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
