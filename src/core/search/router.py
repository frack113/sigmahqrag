"""Semantic router for query-to-collection classification.

Uses a lightweight LLM call to classify user queries into the most
relevant Qdrant collection(s), reducing unnecessary searches across
all three collections.
"""

from __future__ import annotations

import json
import logging
import re

from src.infrastructure.llm.llamacpp.client import LlamaClient

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """\
You are a query classifier for a Sigma detection-rule RAG system.
Classify the user query into the most relevant collection(s).

Collections:
- sigma_rules: Detection rules (YARA, Sigma, Splunk queries, MITRE ATT&CK techniques, threat hunting, IOCs, log sources)
- sigma_docs: Documentation (architecture, setup, configuration, how-to guides, explanations)
- sigma_spec: Specification reference (YAML format, field definitions, schema, syntax, encoding rules, modifiers, tags, logsource taxonomy, correlation rules, filters, FAQ level/status definitions)

Examples of sigma_spec queries: "What severity levels exist", "How do I write a correlation rule", "What does the contains modifier do", "How to tag a MITRE technique", "What logsource for Windows Security", "How are maps evaluated", "What filename conventions for Sigma rules", "How does group-by work", "What is the difference between temporal and temporal_ordered"

Return ONLY a JSON object with a single key "collections" containing a list of collection names.
Examples:
{"collections": ["sigma_rules"]}
{"collections": ["sigma_spec"]}
{"collections": ["sigma_rules", "sigma_spec"]}
{"collections": ["sigma_docs", "sigma_spec"]}
{"collections": ["sigma_rules", "sigma_docs", "sigma_spec"]}

User query: {query}

{"collections": """

# Valid collection names
VALID_COLLECTIONS = {"sigma_rules", "sigma_docs", "sigma_spec"}

# Default fallback: search all collections
DEFAULT_COLLECTIONS = ["sigma_rules", "sigma_docs", "sigma_spec"]


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


async def route_query(
    query: str,
    llm_client: LlamaClient | None = None,
    timeout: float = 5.0,
) -> list[str]:
    """Classify a query into relevant collection(s) using the LLM.

    Args:
        query: The user's search query
        llm_client: Optional LlamaClient instance. When not provided,
            creates a new LlamaClient (fallback for standalone use).
        timeout: LLM call timeout in seconds

    Returns:
        List of collection names to search. Falls back to all collections
        on any error or ambiguous classification.
    """
    if not query.strip():
        return list(DEFAULT_COLLECTIONS)

    try:
        client = llm_client or LlamaClient()
        prompt = ROUTER_PROMPT.format(query=query)

        raw_text = await client.generate(prompt=prompt, temperature=0.0, max_tokens=64)
        collections = _parse_llm_response(raw_text)

        if not collections:
            logger.warning("Router LLM returned invalid response: %s", raw_text[:200])
            return list(DEFAULT_COLLECTIONS)

        logger.info("Router classified query into: %s", collections)
        return collections

    except Exception as e:
        logger.warning("Router failed, falling back to all collections: %s", e)
        return list(DEFAULT_COLLECTIONS)
