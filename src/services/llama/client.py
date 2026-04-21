"""Llama.cpp client."""

from typing import Any


class LlamaClient:
    """Client for llama.cpp server."""

    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        """Initialize the client."""
        self.base_url = base_url

    async def complete(self, prompt: str) -> str:
        """Generate completion."""
        return ""

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        """Generate chat completion."""
        return ""
