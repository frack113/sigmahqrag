"""
LLM Service for SigmaHQ RAG application.

Provides LLM interaction capabilities including streaming support
for slow local LLMs like LM Studio.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from .logging_service import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    Service for interacting with LLMs via HTTP/REST API.

    Supports LM Studio and other OpenAI-compatible APIs with streaming.

    Features:
    - Streaming response support
    - Chat completion with system prompts
    - Error handling and retry logic
    - Configurable timeouts
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize LLM service.

        Args:
            config: Dictionary with LLM configuration (model, base_url, api_key, etc.)
        """
        self.config = config
        self._initialized = False
        logger.info(f"LLMService initialized with config: {config}")

    async def initialize(self) -> bool:
        """Initialize the LLM service."""
        if not self._initialized:
            try:
                self._initialized = True
                logger.info("LLMService initialized")
                return True
            except Exception as e:
                logger.error(f"Error initializing LLMService: {e}")
                return False

    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False
        logger.info("LLMService cleaned up")

    async def simple_completion(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        """
        Generate a non-streaming completion/response.

        Args:
            prompt: User's input prompt
            system_prompt: Optional system message to guide response

        Returns:
            The generated response as string
        """
        try:
            result = await self._completion(prompt, system_prompt, stream=False)
            return str(result) if result else "No response generated"
        except Exception as e:
            logger.error(f"Error in simple_completion: {e}")
            error_msg = f"Error: {str(e)}"
            return error_msg

    async def streaming_completion(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming completion/response.

        Args:
            prompt: User's input prompt
            system_prompt: Optional system message to guide response

        Yields:
            Response chunks as strings
        """
        try:
            async for chunk in self._completion(prompt, system_prompt, stream=True):
                yield chunk
        except Exception as e:
            logger.error(f"Error in streaming_completion: {e}")
            yield f"\n[Error: {str(e)}]\n"

    async def _completion(
        self, prompt: str, system_prompt: str | None = None, stream: bool = False
    ) -> Any:
        """
        Internal method to handle completion requests.

        Args:
            prompt: User's input prompt
            system_prompt: Optional system message
            stream: Whether to use streaming

        Returns:
            Response content (string or async generator)
        """
        model = self.config.get("model", "qwen/qwen3.5-9b")
        base_url = self.config.get("base_url", "http://localhost:1234")
        api_key = self.config.get("api_key", "lm-studio")
        temperature = self.config.get("temperature", 0.7)
        max_tokens = self.config.get("max_tokens", 512)

        if system_prompt and not prompt.startswith(system_prompt):
            # Add system prompt as first message in chat format
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        # Prepare request data
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if not stream:
            payload["stream"] = False

        # Make HTTP request with streaming support
        return await self._make_request(base_url, api_key, payload)

    async def _make_request(
        self, base_url: str, api_key: str, payload: dict[str, Any]
    ) -> Any:
        """
        Make HTTP request to LLM API.

        Args:
            base_url: Base URL of the LLM server
            api_key: API key for authentication
            payload: Request payload

        Returns:
            Response content
        """
        import httpx

        url = f"{base_url}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Accept": "application/json" if not payload.get("stream") else "text/event-stream",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                if payload.get("stream"):
                    # Handle streaming response
                    async def stream_response():
                        async for line in response.aiter_lines():
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    # Parse SSE chunk
                                    obj = json.loads(data)
                                    content = obj.get("choices", [{}])[0].get(
                                        "delta", {}
                                    ).get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    pass

                    return stream_response()
                else:
                    # Parse JSON response
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return content if content else ""
                    return ""

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e}")
                raise RuntimeError(f"Llm Studio API error: {str(e)}")
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise RuntimeError(f"Llm Studio request failed: {str(e)}")

    async def get_model_info(self) -> dict[str, Any]:
        """Get information about available models."""
        try:
            import httpx

            base_url = self.config.get("base_url", "http://localhost:1234")
            api_key = self.config.get("api_key", "lm-studio")

            url = f"{base_url}/v1/models"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}" if api_key else "",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {"error": str(e)}

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Factory function for creating LLM service instances
def create_llm_service(config: dict[str, Any]) -> LLMService:
    """
    Create an LLM service instance with the given configuration.

    Args:
        config: Configuration dictionary for the LLM service

    Returns:
        Initialized LLM service instance
    """
    return LLMService(config)


def get_llm_service(
    model: str = "qwen/qwen3.5-9b",
    base_url: str = "http://localhost:1234",
    api_key: str = "lm-studio",
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> LLMService:
    """
    Get or create an LLM service instance with default configuration.

    Args:
        model: Model identifier
        base_url: Base URL of the LLM server
        api_key: API key for authentication
        temperature: Temperature parameter for generation
        max_tokens: Maximum number of tokens in response

    Returns:
        Configured LLM service instance
    """
    return create_llm_service(
        {
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    )