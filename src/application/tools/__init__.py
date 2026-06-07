"""Tool-calling infrastructure for the Sigma RAG chat system.

Provides:
- ``@tool`` decorator with automatic JSON schema generation
- ``ToolDispatcher`` for async tool execution
- Pre-built Sigma domain tools (search, filter, explain, summarize)

Usage::

    from src.application.tools import get_tools, ToolDispatcher
    from src.application.tools.sigma.tools import ToolContext

    tools = get_tools()
    dispatcher = ToolDispatcher(tools)
    schemas = dispatcher.list_tools()

    # In ChatService:
    response = await llm_client.chat(messages, tools=schemas)
    tool_calls = LlamaClient.parse_tool_calls(response)
"""

from __future__ import annotations

from .executor import ToolDispatcher, ToolExecutionError
from .models import ToolCall, ToolContext, ToolDef, ToolExecutor, ToolResult
from .registry import (
    _FIELD_MAP,
    _VALID_FILTER_FIELDS,
    get_tool_by_name,
    get_tools,
    tool,
)

# Import sigma tools to auto-register them via @tool decorator
from .sigma import tools as _sigma_tools  # noqa: F401

__all__ = [
    "ToolCall",
    "ToolContext",
    "ToolDef",
    "ToolDispatcher",
    "ToolExecutionError",
    "ToolExecutor",
    "ToolResult",
    "_FIELD_MAP",
    "_VALID_FILTER_FIELDS",
    "get_tool_by_name",
    "get_tools",
    "tool",
]
