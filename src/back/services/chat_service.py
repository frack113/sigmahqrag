"""Chat service for processing messages and managing sessions."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from src.back.services.rag_pipeline import RAGPipeline
from src.back.services.sigma_validator import SigmaValidator
from src.back.services.translate_service import (
    detect_sigma_yaml,
    extract_yaml_block,
    translate_detection,
)
from src.rag.search import SearchEngine
from src.shared.schemas.chat_mode import ChatMode

logger = logging.getLogger(__name__)

MAX_HISTORY = 50


class ChatService:
    """Service layer for chat operations."""

    def __init__(self, use_router: bool = True) -> None:
        self.search_engine = SearchEngine(use_router=use_router)
        self.rag_pipeline = RAGPipeline()
        self.validator = SigmaValidator()
        self._history: list[dict[str, str]] = []
        self._uploaded_rule: dict[str, Any] | None = None
        self._last_citations: list[str] = []
        self._current_prompt_id: str = ""

    async def process_message(
        self,
        message: str,
        mode: str = ChatMode.SEARCH.value,
        model: str = "",
        prompt_id: str = "",
    ) -> str:
        """Process a chat message based on the current mode.

        Args:
            message: User message text
            mode: Chat mode (search, coverage, explain)
            model: Selected LLM model path
            prompt_id: Selected system prompt ID

        Returns:
            AI response text
        """
        if not message.strip():
            return ""

        self._add_to_history("user", message)
        self._current_prompt_id = prompt_id

        try:
            if mode == ChatMode.EXPLAIN.value:
                response = await self._handle_explain(message)
            elif mode == ChatMode.COVERAGE.value:
                response = await self._handle_coverage(message)
            else:
                response = await self._handle_search(message)
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            response = f"Error processing message: {str(e)}"

        self._add_to_history("assistant", response)
        return response

    async def process_message_stream(
        self,
        message: str,
        mode: str = ChatMode.SEARCH.value,
        model: str = "",
        prompt_id: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream a chat message response based on the current mode."""
        if not message.strip():
            return

        self._add_to_history("user", message)
        self._current_prompt_id = prompt_id
        if model:
            logger.info("Selected model: %s", model)
        if prompt_id:
            logger.info("Selected prompt_id: %s", prompt_id)

        accumulated: list[str] = []
        try:
            if mode == ChatMode.EXPLAIN.value:
                async for token in self._handle_explain_stream(message):
                    accumulated.append(token)
                    yield token
            elif mode == ChatMode.COVERAGE.value:
                async for token in self._handle_coverage_stream(message):
                    accumulated.append(token)
                    yield token
            else:
                async for token in self._handle_search_stream(message):
                    accumulated.append(token)
                    yield token
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            error_text = f"Error processing message: {str(e)}"
            accumulated.append(error_text)
            yield error_text

        self._add_to_history("assistant", "".join(accumulated))

    async def _handle_search(self, message: str) -> str:
        """Handle search mode: semantic search over indexed Sigma rules.

        If the message contains a Sigma detection YAML block, it is
        automatically translated into plain English and included as
        additional context in the LLM prompt.
        """
        # Auto-detect and translate Sigma YAML
        translation = ""
        if detect_sigma_yaml(message):
            yaml_block = extract_yaml_block(message)
            if yaml_block:
                logger.info("Detected Sigma YAML in chat message — auto-translating")
                translation = await translate_detection(yaml_block, self.rag_pipeline)
                try:
                    await self.rag_pipeline.llm_client.erase_slot_cache()
                except Exception:
                    logger.warning("Failed to clear KV cache after translate")

        results = await self.search_engine.search(message)

        if not results and not translation:
            return "No matching Sigma rules found. Try a different query."

        self._last_citations = [
            self.search_engine.get_citation(r)
            for r in results[:5]
            if self.search_engine.get_citation(r)
        ]

        try:
            # If we have a translation, prepend it as context
            augmented_message = message
            if translation:
                augmented_message = (
                    f"[Auto-translated detection]\n{translation}\n\n[Original YAML]\n{message}"
                )

            return await self.rag_pipeline.answer_search_query(
                augmented_message, results, system_prompt_id=self._current_prompt_id
            )
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return self._fallback_search_results(results)

    async def _handle_explain(self, message: str) -> str:
        """Handle explain mode: analyze uploaded Sigma rule."""
        if not self._uploaded_rule:
            return "No Sigma rule uploaded. Please upload a .yaml file first."

        try:
            related = await self.search_engine.search(self._uploaded_rule.get("name", ""))
            return await self.rag_pipeline.explain_rule(self._uploaded_rule, related)
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return self._fallback_explanation(self._uploaded_rule)

    async def _handle_explain_stream(
        self,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Handle explain mode with streaming."""
        if not self._uploaded_rule:
            yield "No Sigma rule uploaded. Please upload a .yaml file first."
            return

        try:
            related = await self.search_engine.search(self._uploaded_rule.get("name", ""))
            async for token in self.rag_pipeline.explain_rule_stream(self._uploaded_rule, related):
                yield token
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            fallback = self._fallback_explanation(self._uploaded_rule)
            for token in fallback:
                yield token

    async def _handle_coverage(self, message: str) -> str:
        """Handle coverage mode."""
        if not self._uploaded_rule:
            return "No Sigma rule uploaded. Upload a .yaml file to check coverage."

        results = await self.search_engine.search(message)
        if not results:
            return "No related rules found for coverage analysis."

        try:
            return await self.rag_pipeline.analyze_coverage(self._uploaded_rule, results)
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return f"Found {len(results)} related rules for coverage comparison."

    async def _handle_search_stream(
        self,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Handle search mode with streaming: semantic search + LLM token stream.

        If the message contains Sigma YAML, auto-translates and includes
        the translation as context.
        """
        # Auto-detect and translate Sigma YAML
        translation = ""
        if detect_sigma_yaml(message):
            yaml_block = extract_yaml_block(message)
            if yaml_block:
                logger.info("Detected Sigma YAML in chat message — auto-translating")
                translation = await translate_detection(yaml_block, self.rag_pipeline)
                try:
                    await self.rag_pipeline.llm_client.erase_slot_cache()
                except Exception:
                    logger.warning("Failed to clear KV cache after translate")

        results = await self.search_engine.search(message)

        if not results and not translation:
            yield "No matching Sigma rules found. Try a different query."
            return

        self._last_citations = [
            self.search_engine.get_citation(r)
            for r in results[:5]
            if self.search_engine.get_citation(r)
        ]

        if self._last_citations:
            yield f"__CITATIONS__:{json.dumps(self._last_citations)}"

        # If we have a translation, prepend it as context
        augmented_message = message
        if translation:
            augmented_message = (
                f"[Auto-translated detection]\n{translation}\n\n[Original YAML]\n{message}"
            )

        try:
            found = False
            async for token in self.rag_pipeline.answer_search_query_stream(
                augmented_message, results, system_prompt_id=self._current_prompt_id
            ):
                yield token
                found = True
            if not found:
                logger.warning("RAG stream returned no tokens — falling back to search results")
                fallback = self._fallback_search_results(results)
                for t in fallback:
                    yield t
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            fallback = self._fallback_search_results(results)
            for token in fallback:
                yield token

    async def _handle_coverage_stream(
        self,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Handle coverage mode with streaming."""
        if not self._uploaded_rule:
            yield "No Sigma rule uploaded. Upload a .yaml file to check coverage."
            return

        results = await self.search_engine.search(message)
        if not results:
            yield "No related rules found for coverage analysis."
            return

        try:
            async for token in self.rag_pipeline.analyze_coverage_stream(
                self._uploaded_rule, results
            ):
                yield token
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            fallback = f"Found {len(results)} related rules for coverage comparison."
            for token in fallback:
                yield token

    async def validate_and_store_yaml(self, content: bytes) -> dict[str, Any]:
        """Validate YAML content and store rule data in session.

        Args:
            content: Raw YAML file content

        Returns:
            Parsed and validated rule dictionary
        """
        rule_data = self.validator.validate(content)
        self._uploaded_rule = rule_data
        self.rag_pipeline.cache.invalidate()
        return rule_data

    def get_last_citations(self) -> list[str]:
        """Get citations from the last search response."""
        return self._last_citations.copy()

    def _fallback_search_results(self, results: list[dict[str, Any]]) -> str:
        """Fallback when RAG pipeline fails."""
        lines = []
        for i, result in enumerate(results[:5], 1):
            text = result.get("text", "")[:300]
            score = result.get("score", 0)
            lines.append(f"{i}. {text} (relevance: {score:.2f})")
        return "\n\n".join(lines)

    def _fallback_explanation(self, rule: dict[str, Any]) -> str:
        """Fallback explanation without LLM."""
        parts = [
            f"**Rule:** {rule.get('name', 'Unknown')}",
            f"**ID:** {rule.get('id', 'N/A')}",
        ]
        if desc := rule.get("description"):
            parts.append(f"**Description:** {desc}")
        return "\n".join(parts)

    def _add_to_history(self, role: str, content: str) -> None:
        """Add a message to chat history (max 50 messages)."""
        self._history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

    def get_history(self) -> list[dict[str, str]]:
        """Get chat history."""
        return self._history.copy()

    async def clear_history(self) -> None:
        """Clear chat history, uploaded rule, and llama.cpp KV cache."""
        self._history.clear()
        self._uploaded_rule = None
        self._last_citations.clear()
        try:
            await self.rag_pipeline.llm_client.erase_slot_cache()
        except Exception:
            logger.warning("Failed to clear llama.cpp KV cache")
