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
from src.back.tools import ToolContext, ToolDispatcher, get_tools
from src.rag.search import SearchEngine
from src.shared.schemas.chat_mode import ChatMode

logger = logging.getLogger(__name__)

MAX_HISTORY = 50
MAX_TOOL_CALLS = 5


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

        # Tool-calling setup
        self._tool_executor = ToolDispatcher(get_tools())
        self._tool_context = ToolContext(
            search_engine=self.search_engine,
            rag_pipeline=self.rag_pipeline,
        )

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for the LLM."""
        return self._tool_executor.list_tools()

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

    async def _execute_tool_calls(self, messages: list[dict[str, Any]]) -> str:
        """Execute tool calls returned by the LLM in a multi-turn loop.

        1. Send messages + tool schemas to LLM
        2. If LLM returns tool_calls → execute them → append results → repeat
        3. If LLM returns text → return it
        4. Bail out after MAX_TOOL_CALLS iterations

        Returns the final assistant text response.
        """
        schemas = self._get_tool_schemas()
        turns = 0

        while turns < MAX_TOOL_CALLS:
            turns += 1

            # Send chat request with tools and get raw response
            tool_response = await self._send_chat_with_tools(messages, schemas)
            choices = tool_response.get("choices") or []
            if not choices:
                return "No response from model."

            message = choices[0].get("message") or {}
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                # LLM returned text, done
                return message.get("content", "")

            # Execute each tool call
            tool_messages = [message] if "content" in message else []
            for tc in tool_calls:
                tc_id = tc.get("id", "")
                func = tc.get("function", {})
                fn_name = func.get("name", "")
                fn_args_str = func.get("arguments", "{}")

                try:
                    fn_args = json.loads(fn_args_str) if fn_args_str else {}
                except (json.JSONDecodeError, TypeError):
                    fn_args = {}

                try:
                    result = await self._tool_executor.execute(fn_name, fn_args, tc_id)
                    tool_result = {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": result.content,
                    }
                except Exception as e:
                    logger.warning("Tool '%s' failed: %s", fn_name, e)
                    tool_result = {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": f"Error: {e}",
                    }

                tool_messages.append(tool_result)

            messages.extend(tool_messages)

        logger.warning("Max tool call iterations (%d) reached", MAX_TOOL_CALLS)
        return "Too many tool calls. Please simplify your request."

    async def _send_chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Send a chat request with tools and return the raw JSON response."""
        import httpx

        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
            "stream": False,
            "tools": tools,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.rag_pipeline.llm_client.base_url}/v1/chat/completions",
                    json=payload,
                    timeout=120.0,
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error("Tool-calling chat failed: %s", e)
                raise

    async def _handle_search(self, message: str) -> str:
        """Handle search mode: multi-turn tool-calling loop.

        Uses search_sigma, filter_metadata, explain_detection, explain_rule,
        and summarize tools to answer questions about Sigma detection rules.
        """
        assistant_message = {
            "role": "assistant",
            "content": message,
        }
        system_msg = {
            "role": "system",
            "content": (
                "You are a Sigma rule assistant. Use the provided tools to answer "
                "questions about Sigma detection rules. If the user asks about Sigma "
                "rules, use search_sigma. If they want to filter, use filter_metadata. "
                "If they ask to explain a Sigma detection, use explain_detection. "
                "If they ask to explain a full Sigma rule, use explain_rule. "
                "If they want a summary of text, use summarize. Always use tools when appropriate."
            ),
        }
        messages = [system_msg, assistant_message]
        return await self._execute_tool_calls(messages)

    async def _handle_explain(self, message: str) -> str:
        """Handle explain mode: analyze uploaded Sigma rule."""
        if not self._uploaded_rule:
            return "No Sigma rule uploaded. Please upload a .yaml file first."

        related = await self.search_engine.search(self._uploaded_rule.get("name", ""))
        return await self.rag_pipeline.explain_rule(self._uploaded_rule, related)

    async def _handle_explain_stream(
        self,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Handle explain mode with streaming."""
        if not self._uploaded_rule:
            yield "No Sigma rule uploaded. Please upload a .yaml file first."
            return

        related = await self.search_engine.search(self._uploaded_rule.get("name", ""))
        async for token in self.rag_pipeline.explain_rule_stream(self._uploaded_rule, related):
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
                logger.warning("RAG stream returned no tokens")
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")

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
