"""Chat service for processing messages and managing sessions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from src.core.services.rag_pipeline import RAGPipeline
from src.core.services.sigma_validator import SigmaValidator
from src.rag.search import SearchEngine
from src.schemas.chat_mode import ChatMode

logger = logging.getLogger(__name__)

MAX_HISTORY = 50


class ChatService:
    """Service layer for chat operations."""

    def __init__(self) -> None:
        self.search_engine = SearchEngine()
        self.rag_pipeline = RAGPipeline()
        self.validator = SigmaValidator()
        self._history: list[dict[str, str]] = []
        self._uploaded_rule: dict[str, Any] | None = None
        self._last_citations: list[str] = []

    async def process_message(
        self,
        message: str,
        mode: str = ChatMode.SEARCH.value,
    ) -> str:
        """Process a chat message based on the current mode.

        Args:
            message: User message text
            mode: Chat mode (search, coverage, explain)

        Returns:
            AI response text
        """
        if not message.strip():
            return ""

        self._add_to_history("user", message)

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

    async def _handle_search(self, message: str) -> str:
        """Handle search mode: semantic search over indexed Sigma rules."""
        results = await self.search_engine.search(message)

        if not results:
            return "No matching Sigma rules found. Try a different query."

        self._last_citations = [
            self.search_engine.get_citation(r)
            for r in results[:5]
            if self.search_engine.get_citation(r)
        ]

        try:
            return await self.rag_pipeline.answer_search_query(message, results)
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return self._fallback_search_results(results)

    async def _handle_explain(self, message: str) -> str:
        """Handle explain mode: analyze uploaded Sigma rule."""
        if not self._uploaded_rule:
            return "No Sigma rule uploaded. Please upload a .yaml file first."

        try:
            related = await self.search_engine.search(
                self._uploaded_rule.get("name", "")
            )
            return await self.rag_pipeline.explain_rule(self._uploaded_rule, related)
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return self._fallback_explanation(self._uploaded_rule)

    async def _handle_coverage(self, message: str) -> str:
        """Handle coverage mode."""
        if not self._uploaded_rule:
            return "No Sigma rule uploaded. Upload a .yaml file to check coverage."

        results = await self.search_engine.search(message)
        if not results:
            return "No related rules found for coverage analysis."

        try:
            return await self.rag_pipeline.analyze_coverage(
                self._uploaded_rule, results
            )
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return f"Found {len(results)} related rules for coverage comparison."

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

    def clear_history(self) -> None:
        """Clear chat history and uploaded rule."""
        self._history.clear()
        self._uploaded_rule = None
        self._last_citations.clear()
