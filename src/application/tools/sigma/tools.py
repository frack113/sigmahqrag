"""Five Sigma-domain async tool functions.

Each function is decorated with ``@tool`` so it is automatically
registered in the ``ToolDispatcher`` with a JSON schema derived from
its signature and docstring.

Tools that need backend access receive a :class:`ToolContext` object
via the injected ``ctx`` keyword-only parameter.
"""

from __future__ import annotations

import logging
from typing import Any

from ..models import ToolContext
from ..registry import _VALID_FILTER_FIELDS, tool

logger = logging.getLogger(__name__)
# Additional services can be added here as needed


# ------------------------------------------------------------------
# Tool 1: search_sigma
# ------------------------------------------------------------------


@tool
async def search_sigma(*, query: str, ctx: ToolContext | None = None) -> str:
    """Search Sigma rules by natural language query.

    Performs semantic search across sigma_rules, sigma_docs, and
    sigma_spec collections. Returns the top 5 most relevant results
    with metadata and relevance scores.

    :param query: Search query describing the threat or behavior.
    :param ctx: Internal context (do not pass manually).
    """
    if not ctx:
        return "Error: tool context not available."

    try:
        results = await ctx.search_engine.search(query, top_k=5)
        if not results:
            return "No matching Sigma rules found for the given query."

        lines = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            title = meta.get("title", "")
            rule_id = meta.get("rule_id", "")
            score = r.get("score", 0)
            text = (r.get("text") or "")[:300]
            lines.append(
                f"{i}. {title or rule_id or 'Untitled'} (relevance: {score:.2f})\n   {text}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        logger.error("search_sigma failed: %s", e)
        return "Error performing search. Please try again."


# ------------------------------------------------------------------
# Tool 2: filter_metadata
# ------------------------------------------------------------------


@tool
async def filter_metadata(
    *,
    field: str,
    value: str,
    ctx: ToolContext | None = None,
) -> str:
    """Filter Sigma rules by metadata field and value.

    Supports the following fields: author, cve, mitre, level, status,
    logsource_product, logsource_category, source.

    :param field: Metadata field to filter on.
    :param value: Value to match.
    :param ctx: Internal context (do not pass manually).
    """
    if field not in _VALID_FILTER_FIELDS:
        valid = ", ".join(sorted(_VALID_FILTER_FIELDS))
        raise ValueError(f"Invalid field '{field}'. Valid fields are: {valid}")

    if not ctx:
        return "Error: tool context not available."

    try:
        results = await ctx.search_engine.search(
            query=value,
            metadata_filter={field: value},
            top_k=10,
        )

        if not results:
            return f"No rules found with {field}='{value}'."

        lines = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            title = meta.get("title", "Untitled")
            score = r.get("rrf_score", r.get("score", 0))
            lines.append(f"{i}. {title} (relevance: {score:.2f})")
        return "\n\n".join(lines)
    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error("filter_metadata failed: %s", e, exc_info=True)
        return f"Error filtering by {field}='{value}': {e}"


# ------------------------------------------------------------------
# Tool 3: explain_detection
# ------------------------------------------------------------------


@tool
async def explain_detection(
    *,
    rule_yaml: str,
    ctx: ToolContext | None = None,
) -> str:
    """Translate a Sigma detection block into plain English.

    Provides a one-to-one mapping of detection conditions to
    human-readable descriptions, suitable for analysts who need
    to understand what a rule detects without reading YAML.

    :param rule_yaml: The Sigma detection YAML text to translate.
    :param ctx: Internal context (do not pass manually).
    """
    if not ctx:
        return "Error: tool context not available."

    try:
        # Search theSigma spec for context
        search_results = await ctx.search_engine.search(rule_yaml, top_k=5)
        search_context = _format_search_context(search_results)

        # Build prompt
        from src.application.system_prompt import get_prompt_by_id

        prompt_obj = get_prompt_by_id("vulgarisation-english")
        if prompt_obj:
            from jinja2 import Environment, Undefined

            env = Environment(undefined=Undefined)
            template = env.from_string(prompt_obj.content)
            prompt = template.render(search_results=search_context)
        else:
            prompt = (
                "You are a Sigma rule translator. Translate the following "
                "Sigma detection block into plain English. Be concise and clear.\n\n"
                f"Reference context:\n{search_context}\n\nDetection YAML:\n{rule_yaml}"
            )

        translation = await ctx.llm_client.chat(
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        "Translate the detection above into plain English.\n\n"
                        f"Detection YAML:\n{rule_yaml}"
                    ),
                },
            ],
            temperature=0.1,
            stop=[
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
            ],
        )

        # Reformulate into natural language
        if translation:
            try:
                reformulated = await ctx.llm_client.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a plain-English rewriter. Take the following "
                                "technical description and rewrite it as a single, "
                                "clear, natural paragraph. Keep it concise (2-4 sentences)."
                            ),
                        },
                        {"role": "user", "content": translation},
                    ],
                    temperature=0.1,
                )
                if reformulated and len(reformulated) > 20:
                    translation = reformulated
            except Exception:
                logger.warning("Reformulation pass failed, keeping raw translation")

        return translation or "Could not generate translation."
    except Exception as e:
        logger.error("explain_detection failed: %s", e)
        return "Error translating detection. Please try again."


# ------------------------------------------------------------------
# Tool 4: explain_rule
# ------------------------------------------------------------------


@tool
async def explain_rule(
    *,
    rule_yaml: str,
    ctx: ToolContext | None = None,
) -> str:
    """Analyze a Sigma rule and explain its security purpose.

    Provides tactical analysis including attack techniques detected,
    MITRE mapping inference, and detection quality assessment.

    :param rule_yaml: Complete Sigma rule YAML to analyze.
    :param ctx: Internal context (do not pass manually).
    """
    if not ctx:
        return "Error: tool context not available."

    if not ctx.rag_pipeline:
        return "explain_rule requires a RAG pipeline (not available in this context)."

    try:
        import yaml

        rule_data = yaml.safe_load(rule_yaml) if rule_yaml else {}
        if not rule_data:
            return "Could not parse the provided YAML."

        # Find related rules
        related = await ctx.search_engine.search(rule_data.get("title", ""), top_k=5)

        # Use RAG pipeline's explain_rule
        return await ctx.rag_pipeline.explain_rule(rule_data, related)
    except Exception as e:
        logger.error("explain_rule failed: %s", e)
        return "Error analyzing rule. Please try again."


# ------------------------------------------------------------------
# Tool 5: summarize
# ------------------------------------------------------------------


@tool
async def summarize(*, text: str, ctx: ToolContext | None = None) -> str:
    """Condense a long text into a concise summary.

    Compresses verbose content (detection logic, rule explanations)
    into key findings — distinct from explaining which focuses on
    translating technical details.

    :param text: The text to summarize.
    :param ctx: Internal context (do not pass manually).
    """
    if not ctx:
        return "Error: tool context not available."

    try:
        prompt = (
            "Summarize the following text in 3-5 bullet points. "
            "Focus on key findings, technical details, and security-relevant information.\n\n"
            f"Text to summarize:\n{text}"
        )

        response = await ctx.llm_client.chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Please provide a concise summary."},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        return response or "Could not generate summary."
    except Exception as e:
        logger.error("summarize failed: %s", e)
        return "Error summarizing text. Please try again."


def _format_search_context(results: list[dict[str, Any]]) -> str:
    """Format search results into a context string for prompts."""
    if not results:
        return "(no reference material found)"

    parts = []
    for i, r in enumerate(results[:3], 1):
        text = (r.get("text") or "")[:200]
        score = r.get("score", 0)
        parts.append(f"[{i}] (score: {score:.2f}) {text}")

    return "\n\n".join(parts)
