"""
Anthropic LLM Client

Integration with Anthropic API (Claude)
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


class AnthropicClient(BaseLLMClient):
    """
    Anthropic API client for Claude models.

    Supported models:
    - claude-3-opus-20240229
    - claude-3-sonnet-20240229
    - claude-3-haiku-20240307
    """

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-sonnet)
        """
        super().__init__(api_key, model)
        self.base_url = "https://api.anthropic.com/v1"
        self.client = httpx.AsyncClient(
            timeout=120.0,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
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
        Generate text using Anthropic API.

        Args:
            messages: Conversation messages
            temperature: Randomness (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic-specific parameters

        Returns:
            LLMResponse with generated content
        """
        try:
            # Separate system message from conversation
            system_message = None
            conversation_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    conversation_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": conversation_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # Add system message if present
            if system_message:
                payload["system"] = system_message

            # Add optional parameters
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                payload["top_k"] = kwargs["top_k"]

            # Make API request
            response = await self.client.post(
                f"{self.base_url}/messages",
                json=payload,
            )

            # Handle errors
            if response.status_code == 401:
                raise LLMAuthenticationError("Invalid Anthropic API key")
            elif response.status_code == 429:
                raise LLMRateLimitError("Anthropic rate limit exceeded")
            elif response.status_code != 200:
                raise LLMError(f"Anthropic API error: {response.status_code} - {response.text}")

            # Parse response
            data = response.json()
            content = data["content"][0]["text"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=data["model"],
                tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                finish_reason=data.get("stop_reason"),
                metadata={
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                },
            )

        except httpx.TimeoutException:
            raise LLMTimeoutError("Anthropic API request timed out")
        except httpx.HTTPError as e:
            raise LLMError(f"Anthropic HTTP error: {e}")
        except Exception as e:
            raise LLMError(f"Anthropic error: {e}")

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
