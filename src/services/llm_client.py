"""LLM client for local LLM integration (Ollama/LM Studio)."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import httpx

from src.config import load_config

logger = logging.getLogger(__name__)

TIMEOUT = 30.0


class LLMClient:
    """Client for interacting with local LLM API."""

    def __init__(self) -> None:
        config = load_config()
        llama_config = config.get("services", {}).get("llama", {})
        self.base_url = llama_config.get("base_url", "http://localhost:11434")
        self.model = llama_config.get("model_name", "llama3.2")
        self.timeout = TIMEOUT

    async def generate(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The main prompt/question
            context: Additional context (search results, rule data)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response

        Raises:
            httpx.HTTPError: If LLM request fails
        """
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = await response.json()
                return data.get("response", "")

        except httpx.ConnectError:
            logger.error(f"LLM service unavailable at {self.base_url}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM.

        Args:
            prompt: The main prompt/question
            context: Additional context
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Yields:
            Individual tokens/response chunks
        """
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield line

        except httpx.ConnectError:
            logger.error(f"LLM service unavailable at {self.base_url}")
            raise
