"""Reusable Sigma detection translation service.

Provides YAML detection and plain-English translation that can be used
by both the API endpoint and the chat pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from jinja2 import Environment, Undefined

logger = logging.getLogger(__name__)

# Patterns that indicate a Sigma detection YAML block
_SIGMA_PATTERNS = [
    re.compile(r"^\s*detection\s*:", re.MULTILINE),
    re.compile(r"^\s*condition\s*:", re.MULTILINE),
    re.compile(r"^\s*selection\S*\s*:", re.MULTILINE),
    re.compile(r"^\s*filter\S*\s*:", re.MULTILINE),
    re.compile(r"^\s*logsource\s*:", re.MULTILINE),
]

REFORMULATE_SYSTEM = (
    "You are a plain-English rewriter. Take the following technical description "
    "of a security detection rule and rewrite it as a single, clear, natural paragraph. "
    "Do not repeat sentence structures. Do not start multiple sentences with the same words. "
    "Keep it concise (2-4 sentences max)."
)

DEFAULT_TEMPERATURE = 0.1

# Stop sequences to prevent the LLM from hallucinating YAML fields
SIGMA_YAML_STOP_SEQUENCES: list[str] = [
    "\ntitle:",
    "\nid:",
    "\nstatus:",
    "\ndescription:",
    "\nauthor:",
    "\ndate:",
    "\nmodified:",
    "\nreferences:",
    "\ntags:",
    "\nlevel:",
    "\nfields:",
    "\nlogsource:",
    "\nfalsepositives:",
    "\ndetection:",
    "\ncondition:",
]


def _render_safe(template_text: str, **kwargs: Any) -> str:
    """Render a Jinja2 template with user-controlled content safely."""
    env = Environment(undefined=Undefined)
    template = env.from_string(template_text)
    defaults: dict[str, Any] = {
        "search_results": kwargs.get("search_results", ""),
        "question": kwargs.get("question", ""),
    }
    return template.render(defaults)


def detect_sigma_yaml(text: str) -> bool:
    """Check if text contains a Sigma detection YAML block.

    Returns True if at least 2 Sigma-specific patterns are found,
    which reliably distinguishes real Sigma YAML from casual text
    that happens to mention 'detection' or 'condition'.
    """
    matches = sum(1 for p in _SIGMA_PATTERNS if p.search(text))
    return matches >= 2


def extract_yaml_block(text: str) -> str | None:
    """Extract the YAML detection block from a message.

    Tries to find a contiguous YAML block that contains Sigma fields.
    Returns the block text, or None if no valid block is found.
    """
    if not detect_sigma_yaml(text):
        return None

    lines = text.split("\n")
    yaml_lines: list[str] = []
    in_yaml = False

    for line in lines:
        stripped = line.strip()
        # Start of a YAML block: indented content or known Sigma keys
        if re.match(r"^(detection|selection|filter|condition|logsource)\s*:", stripped):
            in_yaml = True

        if in_yaml:
            yaml_lines.append(line)
            # Stop if we hit a non-indented line that isn't a YAML key
            if yaml_lines and stripped and not line.startswith(" ") and not line.startswith("\t"):
                if not re.match(r"^(detection|selection|filter|condition|logsource)\s*:", stripped):
                    # Check if this line is part of YAML (indented or a key)
                    if not any(c in stripped for c in [":", "|", "&", "*", "-"]):
                        yaml_lines.pop()  # Remove trailing non-YAML line
                        break

    if yaml_lines:
        return "\n".join(yaml_lines).strip()
    return text.strip() if detect_sigma_yaml(text) else None


async def translate_detection(
    yaml_text: str,
    rag_pipeline: Any,
    prompt_id: str = "vulgarisation-english",
    use_chat: bool = True,
) -> str:
    """Translate a Sigma detection block into plain English.

    Args:
        yaml_text: The Sigma detection YAML text.
        rag_pipeline: RAGPipeline instance (provides search_engine + llm_client).
        prompt_id: System prompt ID for translation.
        use_chat: Use chat completions endpoint.

    Returns:
        Plain English translation, or empty string on failure.
    """
    from src.application.system.prompts import get_prompt_by_id

    if not yaml_text or not yaml_text.strip():
        return ""

    try:
        # Search the Sigma spec for context
        results = await rag_pipeline.search_engine.search(yaml_text, top_k=5)

        # Get the translation prompt
        prompt_obj = get_prompt_by_id(prompt_id)
        if prompt_obj is None:
            logger.warning("Prompt '%s' not found, using minimal fallback", prompt_id)
            search_context = _format_search_context(results)
            prompt = (
                "You are a Sigma rule translator. Translate the following Sigma detection "
                "block into plain English. Be concise and clear.\n\n"
                f"Reference context:\n{search_context}"
            )
        else:
            search_context = _format_search_context(results)
            prompt = _render_safe(prompt_obj.content, search_results=search_context)

        # First pass: translate
        if use_chat:
            translation = await rag_pipeline.llm_client.chat(
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            "Translate the detection above into plain English.\n\n"
                            f"Detection YAML:\n{yaml_text}"
                        ),
                    },
                ],
                temperature=DEFAULT_TEMPERATURE,
                stop=SIGMA_YAML_STOP_SEQUENCES,
            )
        else:
            translation = await rag_pipeline.llm_client.generate(
                prompt=f"{prompt}\n\nInput to translate:\n{yaml_text}",
                temperature=DEFAULT_TEMPERATURE,
            )

        # Second pass: reformulate into natural language
        if use_chat and translation:
            try:
                reformulated = await rag_pipeline.llm_client.chat(
                    messages=[
                        {"role": "system", "content": REFORMULATE_SYSTEM},
                        {"role": "user", "content": translation},
                    ],
                    temperature=DEFAULT_TEMPERATURE,
                )
                if reformulated and len(reformulated) > 20:
                    translation = reformulated
            except Exception:
                logger.warning("Reformulation pass failed, keeping raw translation")

        return translation or ""

    except Exception as e:
        logger.error("translate_detection failed: %s", e)
        return ""


def _format_search_context(results: list[dict[str, Any]]) -> str:
    """Format search results into a context string for the prompt."""
    if not results:
        return "(no reference material found)"

    parts = []
    for i, r in enumerate(results[:3], 1):
        text = r.get("text", "")[:200]
        score = r.get("score", 0)
        parts.append(f"[{i}] (score: {score:.2f}) {text}")

    return "\n\n".join(parts)
