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
        from src.config.settings import get_config

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
                response.encoding = "utf-8"
                payload = response.json()
                choices = payload.get("choices") or []
                if not choices:
                    return ""
                text = choices[0].get("text")
                return text if text is not None else ""
            except Exception as e:
                raise RuntimeError(f"Llama.cpp generate failed: {e}") from e

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 512,
        stop: list[str] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> str:
        """Generate text via /v1/chat/completions (OpenAI-compatible chat format).

        Reasoning-tuned instruction models follow chat-format prompts more
        reliably than raw text completion, especially for tasks where the
        prompt contains code or YAML the model might otherwise try to
        continue instead of translating.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": str}.
            temperature: Sampling temperature.
            max_tokens: Hard cap on generated tokens.
            stop: Optional list of stop strings (e.g. ["\\nfields:"]).
            tools: Optional list of tool definitions for function calling.
                Each tool is a dict with "type": "function" and "function" key.
            tool_choice: Force or disable tool usage. Use "auto", "none",
                "required", or a specific tool dict.

        Returns:
            Assistant message content, or empty string if the response has
            no choices / content.  When the server supports tools, the
            caller should check for ``tool_calls`` in the response and
            dispatch them manually.
        """
        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    timeout=120.0,
                )
                response.raise_for_status()
                response.encoding = "utf-8"
                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    return ""
                message = choices[0].get("message") or {}
                content = message.get("content")
                return content if content is not None else ""
            except Exception as e:
                raise RuntimeError(f"Llama.cpp chat failed: {e}") from e

    @staticmethod
    def parse_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract tool_calls from an OpenAI-compatible chat completion response.

        Returns an empty list when:
        - The response has no choices
        - The message has no tool_calls field
        - The model does not support tools (no tool_calls key)
        """
        choices = response.get("choices") or []
        if not choices:
            return []
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        return list(tool_calls)

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
                    response.encoding = "utf-8"
                    raw_lines: list[str] = []
                    data_lines: list[str] = []
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
