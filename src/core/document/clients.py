"""LLM client abstraction for enrichment across all RAG transforms.

Provides a thread-safe singleton ``_StaticLlamaClient`` and lazy accessor
``get_llm_client()`` so every transform can call an LLM without importing
``httpx`` or managing singleton lifecycle locally.
"""

from __future__ import annotations

import logging
import threading

import httpx

from llama_index.llms.openai_like import OpenAILike

logger = logging.getLogger(__name__)


class _StaticLlamaClient:
    """Minimal sync wrapper around LlamaIndex's ``OpenAILike`` for LLM enrichment (summary + keywords)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
        self.base_url = base_url.rstrip("/")
        self._llm = OpenAILike(
            model="sigma",
            api_base=f"{self.base_url}/v1",
            api_key="sigma-key",
            context_window=128000,
            is_chat_model=False,
            timeout=15.0,
        )

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        try:
            resp = self._llm.complete(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
            return resp.text or ""
        except Exception as e:
            logger.debug("LLM enrichment failed: %s", e)
            return ""

    def erase_slot_cache(self, slot_id: int = 0) -> None:
        """Erase the KV cache for a given slot to prevent llama.cpp context explosion."""
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/slots/{slot_id}?action=erase",
                    content=b"",
                )
                if resp.status_code == 200:
                    logger.debug("KV cache erased for slot %d", slot_id)
                else:
                    logger.warning(
                        "erase_slot_cache returned %d for slot %d",
                        resp.status_code,
                        slot_id,
                    )
        except Exception:
            logger.debug("Failed to erase llama.cpp slot cache (likely not available)")


# Global LLM client singleton (lazy-initialized)
_llm_client: _StaticLlamaClient | None = None
_llm_lock = threading.Lock()


def get_llm_client() -> _StaticLlamaClient:
    """Return the thread-safe singleton LLM client."""
    global _llm_client
    if _llm_client is None:
        with _llm_lock:
            if _llm_client is None:
                _llm_client = _StaticLlamaClient()
    return _llm_client
