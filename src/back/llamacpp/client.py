"""Llama.cpp client."""

from typing import Any

import httpx


class LlamaClient:
    """Client for llama.cpp server."""

    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        """Initialize the client."""
        self.base_url = base_url.rstrip("/")

    async def complete(self, prompt: str) -> str:
        """Generate completion."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/completion",
                    json={"prompt": prompt, "temperature": 0.3},
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json().get("content", "")
            except Exception as e:
                raise RuntimeError(f"Llama.cpp completion failed: {e}") from e

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        """Generate chat completion."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={"messages": messages, "temperature": 0.3},
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                raise RuntimeError(f"Llama.cpp chat failed: {e}") from e
