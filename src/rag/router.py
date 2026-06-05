"""Semantic router for query-to-collection classification.

Uses a lightweight LLM call to classify user queries into the most
relevant Qdrant collection(s), reducing unnecessary searches across
all three collections.
"""

from __future__ import annotations

import json
import logging
import re
import threading

import httpx

from src.back.llamacpp.client import LlamaClient

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """\
You are a query classifier for a Sigma detection-rule RAG system.
Classify the user query into the most relevant collection(s).

Collections:
- sigma_rules: Detection rules (YARA, Sigma, Splunk queries, MITRE ATT&CK techniques, threat hunting, IOCs, log sources)
- sigma_docs: Documentation (architecture, setup, configuration, how-to guides, explanations)
- sigma_spec: Specifications (YAML format, field definitions, schema, syntax, encoding rules)

Return ONLY a JSON object with a single key "collections" containing a list of collection names.
Examples:
{"collections": ["sigma_rules"]}
{"collections": ["sigma_rules", "sigma_spec"]}
{"collections": ["sigma_docs", "sigma_spec"]}
{"collections": ["sigma_rules", "sigma_docs", "sigma_spec"]}

User query: {query}

{"collections": """

# Valid collection names
VALID_COLLECTIONS = {"sigma_rules", "sigma_docs", "sigma_spec"}

# Default fallback: search all collections
DEFAULT_COLLECTIONS = ["sigma_rules", "sigma_docs", "sigma_spec"]

# Thread-safe singleton for the LLM client
_llm_client: LlamaClient | None = None
_llm_lock = threading.Lock()


def _get_llm_client() -> LlamaClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    with _llm_lock:
        if _llm_client is not None:
            return _llm_client
        _llm_client = LlamaClient()
    return _llm_client


def reset_llm_client() -> None:
    """Reset the cached LLM client singleton (for testing)."""
    global _llm_client
    with _llm_lock:
        _llm_client = None


def _parse_llm_response(raw: str) -> list[str]:
    """Parse the LLM's JSON response into a list of collection names.

    Handles common LLM quirks: extra whitespace, markdown fences,
    trailing commas, partial output.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try to extract JSON object from the response
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return []

    collections = data.get("collections", [])
    if not isinstance(collections, list):
        return []

    # Validate collection names
    return [c for c in collections if c in VALID_COLLECTIONS]


async def route_query(query: str, timeout: float = 5.0) -> list[str]:
    """Classify a query into relevant collection(s) using the LLM.

    Args:
        query: The user's search query
        timeout: LLM call timeout in seconds

    Returns:
        List of collection names to search. Falls back to all collections
        on any error or ambiguous classification.
    """
    if not query.strip():
        return list(DEFAULT_COLLECTIONS)

    try:
        client = _get_llm_client()
        prompt = ROUTER_PROMPT.format(query=query)

        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{client.base_url}/v1/completions",
                json={
                    "prompt": prompt,
                    "temperature": 0.0,
                    "max_tokens": 64,
                    "stream": False,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()

        choices = payload.get("choices") or []
        if not choices:
            logger.warning("Router LLM returned no choices")
            return list(DEFAULT_COLLECTIONS)

        raw_text = choices[0].get("text", "")
        collections = _parse_llm_response(raw_text)

        if not collections:
            logger.warning("Router LLM returned invalid response: %s", raw_text[:200])
            return list(DEFAULT_COLLECTIONS)

        logger.info("Router classified query into: %s", collections)
        return collections

    except Exception as e:
        logger.warning("Router failed, falling back to all collections: %s", e)
        return list(DEFAULT_COLLECTIONS)
