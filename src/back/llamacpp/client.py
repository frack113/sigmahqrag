"""Llama.cpp HTTP client (talks to llama-server.exe)."""

from typing import Any

import httpx


def _default_base_url() -> str:
    """Resolve the llama base URL from app config, with a safe fallback."""
    try:
        from src.shared import get_config

        return get_config().llama_base_url or "http://127.0.0.1:8080"
    except ImportError:
        return "http://127.0.0.1:8080"


class LlamaClient:
    """Client for the llama-server HTTP API (OpenAI-compatible).

    Defaults to ``services.llama.base_url`` from runtime config so the
    port can be changed via TOML without touching this code.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize the client."""
        self.base_url = (base_url or _default_base_url()).rstrip("/")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> str:
        """Generate text from a single prompt via /v1/completions.

        Named ``generate`` to match the call shape ``RAGPipeline`` uses
        (``self.llm_client.generate(prompt=..., temperature=...)``).
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/completions",
                    json={
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices") or []
                if not choices:
                    return ""
                text = choices[0].get("text")
                return text if text is not None else ""
            except Exception as e:
                raise RuntimeError(f"Llama.cpp generate failed: {e}") from e

    async def complete(self, prompt: str) -> str:
        """Legacy alias for :meth:`generate` (kept for back-compat)."""
        return await self.generate(prompt)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Generate chat completion via OpenAI-compatible endpoint."""
        body: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=body,
                    timeout=120.0,
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices") or []
                if not choices:
                    return ""
                choice = choices[0]
                message = choice.get("message") or {}
                content = message.get("content")
                return content if content is not None else ""
            except Exception as e:
                raise RuntimeError(f"Llama.cpp chat failed: {e}") from e
