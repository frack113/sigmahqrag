"""RAG pipeline service combining search results with LLM generation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from src.back.llamacpp import LlamaClient
from src.back.rag.search import SearchEngine

from .cache import ResponseCache

logger = logging.getLogger(__name__)

PROMPT_DIR = "src/front/templates/prompts"


async def _stream_cache_wrapper(
    pipeline: RAGPipeline,
    cache_key: str,
    stream: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """Wrap a token stream to cache the full response."""
    accumulated: list[str] = []
    try:
        async for token in stream:
            accumulated.append(token)
            yield token
    except Exception:
        pass
    full_text = "".join(accumulated)
    if full_text:
        pipeline.cache.set(cache_key, full_text)


class RAGPipeline:
    """Pipeline for RAG-based chat responses."""

    def __init__(self) -> None:
        self.search_engine = SearchEngine()
        # Was ``LlamaService()``, which is an alias for
        # ``LlamaBinaryService`` — the binary *process manager*, not an
        # LLM client. It has no ``.generate()`` method, so the chat
        # pipeline crashed with AttributeError on the first call.
        # ``LlamaClient`` talks to the llama-server HTTP API.
        self.llm_client = LlamaClient()
        self.cache = ResponseCache()
        self.env = Environment(
            loader=FileSystemLoader(PROMPT_DIR),
            autoescape=True,
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
        rule_yaml = await self._format_rule_yaml(rule_data)
        prompt = template.render(
            uploaded_rule=rule_yaml,
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

    async def explain_rule_stream(
        self,
        rule_data: dict[str, Any],
        related_results: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream explanation for an uploaded Sigma rule."""
        related_text = self._format_search_results(related_results or [])
        cache_key = self.cache.generate_key(
            query=rule_data.get("name", ""),
            context=related_text,
        )

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for rule explanation: {rule_data.get('name')}")
            for token in cached:
                yield token
            return

        template = self.env.get_template("explain_rule.j2")
        rule_yaml = await self._format_rule_yaml(rule_data)
        prompt = template.render(
            uploaded_rule=rule_yaml,
            related_rules=related_text,
        )

        try:
            stream = self.llm_client.generate_stream(
                prompt=prompt,
                temperature=0.3,
            )
            async for token in _stream_cache_wrapper(self, cache_key, stream):
                yield token
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            fallback = self._fallback_explanation(rule_data)
            for token in fallback:
                yield token

    async def answer_search_query_stream(
        self,
        query: str,
        search_results: list[dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Stream answer for a search query using LLM."""
        results_text = self._format_search_results(search_results)
        cache_key = self.cache.generate_key(query=query, context=results_text)

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for search query: {query[:50]}")
            for token in cached:
                yield token
            return

        template = self.env.get_template("search_answer.j2")
        prompt = template.render(
            search_results=results_text,
            question=query,
        )

        try:
            stream = self.llm_client.generate_stream(
                prompt=prompt,
                temperature=0.3,
            )
            async for token in _stream_cache_wrapper(self, cache_key, stream):
                yield token
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            fallback = self._fallback_search_results(search_results)
            for token in fallback:
                yield token

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
        rule_yaml = await self._format_rule_yaml(rule_data)
        prompt = template.render(
            uploaded_rule=rule_yaml,
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
            return f"Found {len(related_results)} related rules for coverage comparison."

    async def analyze_coverage_stream(
        self,
        rule_data: dict[str, Any],
        related_results: list[dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Stream coverage analysis for an uploaded Sigma rule."""
        related_text = self._format_search_results(related_results)
        cache_key = self.cache.generate_key(
            query=rule_data.get("name", ""),
            context=related_text,
        )

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for coverage analysis: {rule_data.get('name')}")
            for token in cached:
                yield token
            return

        template = self.env.get_template("coverage_analysis.j2")
        rule_yaml = await self._format_rule_yaml(rule_data)
        prompt = template.render(
            uploaded_rule=rule_yaml,
            related_rules=related_text,
        )

        try:
            stream = self.llm_client.generate_stream(
                prompt=prompt,
                temperature=0.3,
            )
            async for token in _stream_cache_wrapper(self, cache_key, stream):
                yield token
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            fallback = f"Found {len(related_results)} related rules for coverage comparison."
            for token in fallback:
                yield token

    def _format_search_results(self, results: list[dict[str, Any]]) -> str:
        """Format search results for LLM context with proper citations."""
        if not results:
            return "No related rules found."

        lines = []
        for i, result in enumerate(results[:5], 1):
            text = result.get("text", "")[:800]
            metadata = result.get("metadata", {})
            title = metadata.get("title", "")
            file_name = metadata.get("file_name", "")
            source = metadata.get("source", "")
            rule_id = metadata.get("rule_id", "")
            original_url = metadata.get("original_url", "")

            header_parts = []
            if title:
                header_parts.append(f"Title: {title}")
            if source:
                header_parts.append(f"Source: {source}")
            if file_name:
                header_parts.append(f"File: {file_name}")
            if original_url:
                header_parts.append(f"URL: {original_url}")
            if rule_id:
                header_parts.append(f"Rule ID: {rule_id}")

            header = " | ".join(header_parts) if header_parts else f"Result {i}"
            lines.append(f"---\n{header}\n---\n{text}")

        return "\n\n".join(lines)

    async def _format_rule_yaml(self, rule: dict[str, Any]) -> str:
        """Format rule data as readable YAML-like text."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: yaml.dump(rule, default_flow_style=False, allow_unicode=True)
        )

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
