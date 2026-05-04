"""RAG pipeline service combining search results with LLM generation."""

from __future__ import annotations

import logging
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.core.backend.llamacpp import LlamaService
from src.core.rag.search import SearchEngine

from .cache import ResponseCache

logger = logging.getLogger(__name__)

PROMPT_DIR = "src/templates/prompts"


class RAGPipeline:
    """Pipeline for RAG-based chat responses."""

    def __init__(self) -> None:
        self.search_engine = SearchEngine()
        self.llm_client = LlamaService()
        self.cache = ResponseCache()
        self.env = Environment(
            loader=FileSystemLoader(PROMPT_DIR),
            autoescape=False,
        )

    async def explain_rule(
        self,
        rule_data: dict[str, Any],
        related_results: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate explanation for an uploaded Sigma rule.

        Args:
            rule_data: Parsed Sigma rule dictionary
            related_results: Optional related rules from search

        Returns:
            LLM-generated explanation
        """
        related_text = self._format_search_results(related_results or [])
        cache_key = self.cache.generate_key(
            query=rule_data.get("name", ""),
            context=related_text,
        )

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for rule explanation: {rule_data.get('name')}")
            return cached

        template = self.env.get_template("explain_rule.j2")
        prompt = template.render(
            uploaded_rule=self._format_rule_yaml(rule_data),
            related_rules=related_text,
        )

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
            )
            self.cache.set(cache_key, response)
            return response
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._fallback_explanation(rule_data)

    async def answer_search_query(
        self,
        query: str,
        search_results: list[dict[str, Any]],
    ) -> str:
        """Generate answer for a search query using LLM.

        Args:
            query: User's question
            search_results: Search results from Qdrant

        Returns:
            LLM-generated answer
        """
        results_text = self._format_search_results(search_results)
        cache_key = self.cache.generate_key(query=query, context=results_text)

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for search query: {query[:50]}")
            return cached

        template = self.env.get_template("search_answer.j2")
        prompt = template.render(
            search_results=results_text,
            question=query,
        )

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
            )
            self.cache.set(cache_key, response)
            return response
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._fallback_search_results(search_results)

    async def analyze_coverage(
        self,
        rule_data: dict[str, Any],
        related_results: list[dict[str, Any]],
    ) -> str:
        """Analyze detection coverage gaps.

        Args:
            rule_data: Uploaded Sigma rule
            related_results: Related rules for comparison

        Returns:
            LLM-generated coverage analysis
        """
        related_text = self._format_search_results(related_results)
        cache_key = self.cache.generate_key(
            query=rule_data.get("name", ""),
            context=related_text,
        )

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for coverage analysis: {rule_data.get('name')}")
            return cached

        template = self.env.get_template("coverage_analysis.j2")
        prompt = template.render(
            uploaded_rule=self._format_rule_yaml(rule_data),
            related_rules=related_text,
        )

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
            )
            self.cache.set(cache_key, response)
            return response
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return (
                f"Found {len(related_results)} related rules for coverage comparison."
            )

    def _format_search_results(self, results: list[dict[str, Any]]) -> str:
        """Format search results for LLM context with proper citations."""
        if not results:
            return "No related rules found."

        lines = []
        for i, result in enumerate(results[:5], 1):
            text = result.get("text", "")[:500]
            # Generate citation in format [sigma:rule_id]
            rule_id = result.get("rule_id") or result.get("id") or f"rule_{i}"
            citation = f"sigma:{rule_id}"
            lines.append(f"[{citation}]: {text}")

        return "\n\n".join(lines)

    def _format_rule_yaml(self, rule: dict[str, Any]) -> str:
        """Format rule data as readable YAML-like text."""
        import yaml

        return yaml.dump(rule, default_flow_style=False, allow_unicode=True)

    def _fallback_explanation(self, rule_data: dict[str, Any]) -> str:
        """Fallback explanation without LLM."""
        parts = [
            f"**Rule:** {rule_data.get('name', 'Unknown')}",
            f"**ID:** {rule_data.get('id', 'N/A')}",
        ]
        if desc := rule_data.get("description"):
            parts.append(f"**Description:** {desc}")
        return "\n".join(parts)

    def _fallback_search_results(self, results: list[dict[str, Any]]) -> str:
        """Fallback search results without LLM."""
        if not results:
            return "No matching Sigma rules found."

        lines = []
        for i, result in enumerate(results[:5], 1):
            text = result.get("text", "")[:300]
            lines.append(f"{i}. {text}")

        return "\n\n".join(lines)
