"""Llama.cpp HTTP client (talks to llama-server.exe).

Uses LlamaIndex's OpenAILike for completion and chat operations,
while retaining a minimal httpx fallback for endpoint-specific
calls like slot cache erasure.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any, cast

import httpx

from llama_index.core.llms import ChatMessage
from llama_index.llms.openai_like import OpenAILike

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

    Uses LlamaIndex's ``OpenAILike`` under the hood so the raw ``httpx``
    dependency is removed from the hot path.  Defaults to
    ``services.llama.base_url`` from runtime config so the port can be
    changed via TOML without touching this code.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize the client."""
        self.base_url = (base_url or _default_base_url()).rstrip("/")
        self._llm = OpenAILike(
            model="sigma",
            api_base=f"{self.base_url}/v1",
            api_key="sigma-key",
            context_window=128000,
            is_chat_model=True,
            max_tokens=512,
            timeout=120.0,
        )

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
        try:
            if stream:
                chunks: list[str] = []
                stream_gen = await self._llm.astream_complete(prompt=prompt)
                async for response in stream_gen:
                    chunks.append(response.delta or "")
                return "".join(chunks)
            resp = await self._llm.acomplete(
                prompt=prompt, temperature=temperature, max_tokens=max_tokens
            )
            return resp.text or ""
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
        try:
            chat_messages = [
                ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages
            ]
            resp = await self._llm.achat(
                chat_messages,
                temperature=temperature,
                additional_kwargs={"max_tokens": max_tokens, "stop": stop},
            )
            return resp.message.content or ""
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

    async def chat_raw(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 512,
        stop: list[str] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a chat request and return the raw JSON response dict.

        Useful for tool-calling where the caller needs access to
        ``choices[0].message.tool_calls`` in addition to content.
        """
        from openai import AsyncOpenAI

        chat_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]
        kwargs: dict[str, Any] = {
            "temperature": temperature,
            "additional_kwargs": {"max_tokens": max_tokens, "stop": stop},
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        llm_client = self._llm.openai_client  # type: ignore[attr-defined]
        if not isinstance(llm_client, AsyncOpenAI):
            llm_client = self._llm.async_openai_client  # type: ignore[attr-defined]

        resp = await llm_client.chat.create(
            model=self._llm.model,
            messages=[{"role": m.role, "content": m.content} for m in chat_messages],
            **kwargs,
        )
        return cast(dict[str, Any], resp.model_dump())

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
        try:
            stream_gen = await self._llm.astream_complete(
                prompt=prompt, temperature=temperature, additional_kwargs={"max_tokens": max_tokens}
            )
            async for response in stream_gen:
                if response.delta:
                    yield response.delta
            logger.info("Llama.cpp generate_stream completed")
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
