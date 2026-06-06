"""Shared LLM enrichment utilities for all RAG transforms.

Provides ``enrich_by_llm`` — a single function that:
1. Loads the prompt template from ``templates/prompts/``
2. Formats it with the input text
3. Calls the LLM
4. Parses the structured response (Summary / Keywords)

Usage::

    from rag.transforms.generique.llm import enrich_by_llm

    result = enrich_by_llm(my_text, llm_client)
    summary = result.get("summary") or ""
    keywords = result.get("keywords") or ""
"""

from __future__ import annotations

import functools
import logging
import pathlib

logger = logging.getLogger(__name__)

__all__ = ["enrich_by_llm", "load_enrich_prompt"]

# ---------------------------------------------------------------------------
# Prompt template loading (from templates/prompts/enrich_chunk.md)
# ---------------------------------------------------------------------------
_PROMPTS_DIR = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    / "templates"
    / "prompts"
    / "rag"
)
_enrich_prompt_cache: str | None = None


@functools.lru_cache(maxsize=1)
def load_enrich_prompt() -> str:
    """Load the ``enrich_chunk.md`` prompt template from disk (cached)."""
    path = _PROMPTS_DIR / "enrich_chunk.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("enrich_chunk.md not found at %s — enrichment will likely fail", path)
        return ""


def enrich_by_llm(
    text: str,
    llm_client: object,
    *,
    prompt_template: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.3,
    text_limit: int = 2000,
) -> dict[str, str | None]:
    """Enrich *text* via LLM: format prompt, call model, parse response.

    This is the **single source of truth** for any transform that needs
    LLM-based summary + keyword extraction.  Every chunker and any future
    transform should call this function instead of duplicating the
    prompt-formatting / LLM-call / parsing logic.

    The prompt template is loaded from ``templates/prompts/enrich_chunk.md``
    at module import time.  Pass a custom *prompt_template* only for testing.

    Parameters are deliberately generic — the only contract on
    ``llm_client`` is that it has a ``generate(prompt, max_tokens, temperature)``
    method returning a string.

    Args:
        text: Input text to enrich (truncated to ``text_limit`` in the prompt).
        llm_client: Any object with a ``generate(...)`` method.
        prompt_template: Optional override — uses ``enrich_chunk.md`` from disk by default.
        max_tokens: Maximum generation tokens passed to ``llm_client.generate``.
        temperature: Generation temperature passed to ``llm_client.generate``.
        text_limit: Character cap applied before formatting the prompt.

    Returns:
        A dict with the keys ``"summary"``, ``"keywords"`` and ``"error"``.
        Values are ``str`` or ``None``.
    """
    _default = prompt_template or load_enrich_prompt()

    try:
        raw = llm_client.generate(
            _default.format(text=text[:text_limit]), max_tokens=max_tokens, temperature=temperature
        )
    except Exception as e:
        logger.debug("LLM enrichment failed: %s", e)
        return {"summary": None, "keywords": None, "error": str(e)}

    if not raw:
        return {"summary": None, "keywords": None, "error": None}

    _summary = _keywords = ""
    for part in raw.split("\n\n"):
        part = part.strip()
        if part.startswith("Summary:") or part.startswith("Summary :"):
            _summary = part.replace("Summary:", "").replace("Summary :", "").strip()
        elif part.startswith("Keywords:") or part.startswith("Keywords :"):
            _keywords = part.replace("Keywords:", "").replace("Keywords :", "").strip()

    return {
        "summary": _summary or None,
        "keywords": _keywords or None,
        "error": None,
    }
