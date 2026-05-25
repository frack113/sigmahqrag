"""Llama.cpp HTTP client (talks to llama-server.exe)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

logger = logging.getLogger(__name__)


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
        stream: bool = False,
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
                        "stream": stream,
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

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation via /v1/completions?stream=true.

        Yields individual token strings from llama.cpp SSE events.
        """
        logger.info("Llama.cpp generate_stream called, prompt length: %d", len(prompt))
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/completions",
                    json={
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True,
                        "n_predict": max_tokens,
                    },
                ) as response:
                    logger.info("Llama.cpp stream response status: %d", response.status_code)
                    response.raise_for_status()
                    raw_lines = []
                    data_lines = []
                    line_count = 0
                    async for line in response.aiter_lines():
                        line_count += 1
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            if line_count <= 10:
                                raw_lines.append(f"  line {line_count}: {repr(line)}")
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            logger.info("Llama.cpp stream completed after %d lines", line_count)
                            break
                        if len(data_lines) < 5:
                            data_lines.append(data_str[:300])
                        try:
                            event = json.loads(data_str)
                            choices = event.get("choices") or []
                            if not choices:
                                logger.warning("SSE event has no choices: %s", data_str[:300])
                            for choice in choices:
                                text = choice.get("text")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            logger.debug("Invalid SSE event: %s", data_str[:200])
                    if raw_lines:
                        logger.info(
                            "First %d raw SSE lines (non-data): %s",
                            len(raw_lines),
                            "\n".join(raw_lines),
                        )
                    if data_lines:
                        logger.info("First %d SSE data events: %s", len(data_lines), data_lines)
                    logger.info("Finished reading %d SSE lines", line_count)
            except httpx.TimeoutException:
                logger.error("Llama.cpp generate_stream timed out")
                raise
            except Exception as e:
                logger.error("Llama.cpp generate_stream failed: %s", e)
                raise RuntimeError(f"Llama.cpp generate_stream failed: {e}") from e

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

    async def erase_slot_cache(self, slot_id: int = 0) -> bool:
        """Erase the KV cache for a given slot via ``/slots/{id}?action=erase``.

        This forces llama.cpp to start with a fresh KV cache on the next
        request, effectively resetting the conversation context.

        Returns ``True`` on success, ``False`` if the endpoint is unavailable
        (e.g. older server binary without slot management).
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/slots/{slot_id}?action=erase",
                    content=b"",
                )
                if response.status_code == 200:
                    logger.info("KV cache erased for slot %d", slot_id)
                    return True
                logger.warning(
                    "erase_slot_cache returned %d for slot %d",
                    response.status_code,
                    slot_id,
                )
                return False
            except httpx.ConnectError:
                logger.debug("llama.cpp not reachable — cannot erase slot cache")
                return False
            except Exception:
                logger.exception("Failed to erase llama.cpp slot cache")
                return False
