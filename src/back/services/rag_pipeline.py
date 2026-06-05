"""RAG pipeline service combining search results with LLM generation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import yaml
from jinja2 import Template

from src.back.llamacpp import LlamaClient
from src.rag.search import SearchEngine

from .cache import ResponseCache

logger = logging.getLogger(__name__)


async def _stream_cache_wrapper(
    pipeline: RAGPipeline,
    cache_key: str,
    stream: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """Wrap a token stream to cache the full response."""
    accumulated: list[str] = []
    async for token in stream:
        accumulated.append(token)
        yield token
    full_text = "".join(accumulated)
    if full_text:
        pipeline.cache.set(cache_key, full_text)


class RAGPipeline:
    """Pipeline for RAG-based chat responses."""

    def __init__(self) -> None:
        self.search_engine = SearchEngine()
        self.llm_client = LlamaClient()
        self.cache = ResponseCache()

    def _resolve_prompt(self, prompt_id: str = "", mode: str = "search") -> str:
        """Resolve prompt content from DuckDB by ID or mode.

        Priority:
        1. Explicit prompt_id if provided
        2. Active prompt (search mode only)
        3. Mode-specific default (search-answer, explain-rule, coverage-analysis)
        """
        try:
            from src.back.system_prompt import (
                get_active_prompt,
                get_prompt_by_id,
                get_prompt_by_name,
            )

            if prompt_id:
                p = get_prompt_by_id(prompt_id)
                if p:
                    return p.content
                logger.warning("prompt_id '%s' not found — falling back", prompt_id)

            if mode == "search":
                active = get_active_prompt()
                if active:
                    return active.content

            mode_map = {
                "search": "search-answer",
                "explain": "explain-rule",
                "coverage": "coverage-analysis",
            }
            name = mode_map.get(mode, "search-answer")
            p = get_prompt_by_name(name)
            if p:
                return p.content
        except Exception:
            logger.exception("Failed to resolve prompt for mode=%s id=%s", mode, prompt_id)

        logger.warning(
            "No prompt found for mode=%s id=%s — using minimal fallback", mode, prompt_id
        )
        return "Answer the user's question based on the provided context."

    async def explain_rule(
        self,
        rule_data: dict[str, Any],
        related_results: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate explanation for an uploaded Sigma rule."""
        related_text = self._format_search_results(related_results or [])
        cache_key = self.cache.generate_key(
            query=rule_data.get("name", ""),
            context=related_text,
        )

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for rule explanation: {rule_data.get('name')}")
            return cached

        try:
            prompt_content = self._resolve_prompt(mode="explain")
            rule_yaml = await self._format_rule_yaml(rule_data)
            prompt = Template(prompt_content).render(
                uploaded_rule=rule_yaml,
                related_rules=related_text,
            )

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

        try:
            prompt_content = self._resolve_prompt(mode="explain")
            rule_yaml = await self._format_rule_yaml(rule_data)
            prompt = Template(prompt_content).render(
                uploaded_rule=rule_yaml,
                related_rules=related_text,
            )

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
        system_prompt_id: str = "",
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

        try:
            prompt_content = self._resolve_prompt(system_prompt_id, mode="search")
            prompt = Template(prompt_content).render(
                search_results=results_text,
                question=query,
            )

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
        system_prompt_id: str = "",
    ) -> str:
        """Generate answer for a search query using LLM."""
        results_text = self._format_search_results(search_results)
        cache_key = self.cache.generate_key(query=query, context=results_text)

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for search query: {query[:50]}")
            return cached

        try:
            prompt_content = self._resolve_prompt(system_prompt_id, mode="search")
            prompt = Template(prompt_content).render(
                search_results=results_text,
                question=query,
            )

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
        """Analyze detection coverage gaps."""
        related_text = self._format_search_results(related_results)
        cache_key = self.cache.generate_key(
            query=rule_data.get("name", ""),
            context=related_text,
        )

        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for coverage analysis: {rule_data.get('name')}")
            return cached

        try:
            prompt_content = self._resolve_prompt(mode="coverage")
            rule_yaml = await self._format_rule_yaml(rule_data)
            prompt = Template(prompt_content).render(
                uploaded_rule=rule_yaml,
                related_rules=related_text,
            )

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

        try:
            prompt_content = self._resolve_prompt(mode="coverage")
            rule_yaml = await self._format_rule_yaml(rule_data)
            prompt = Template(prompt_content).render(
                uploaded_rule=rule_yaml,
                related_rules=related_text,
            )

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
            text = result.get("text", "")[:1200]
            metadata = result.get("metadata", {})
            title = metadata.get("title", "")
            file_name = metadata.get("file_name", "")
            source = metadata.get("source", "")
            rule_id = metadata.get("rule_id", "")
            original_url = metadata.get("original_url", "")
            section_title = metadata.get("section_title", "")

            header_parts = []
            if section_title:
                header_parts.append(f"Section: {section_title}")
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
        for i, result in enumerate(results[:2], 1):
            text = result.get("text", "")[:500]
            lines.append(f"{i}. {text}")

        return "\n\n".join(lines)
