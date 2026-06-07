"""Unit tests for tool decorator and ToolDispatcher."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.application.tools.executor import ToolDispatcher
from src.application.tools.registry import tool

# ------------------------------------------------------------------
# @tool decorator
# ------------------------------------------------------------------


class TestToolDecorator:
    """Tests for the @tool decorator."""

    def test_decorator_populates_name(self) -> None:
        @tool
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello {name}"

        assert greet.name == "greet"

    def test_decorator_preserves_docstring(self) -> None:
        @tool
        def do_something(x: int) -> int:
            """Perform an action.

            This does something useful.
            """
            return x * 2

        assert "Perform an action" in do_something.description

    def test_decorator_generates_json_schema(self) -> None:
        @tool
        def multiply(a: float, b: float) -> float:
            """Multiply two numbers."""
            return a * b

        schema = multiply.to_json_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "multiply"
        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "a" in params["properties"]
        assert "b" in params["properties"]

    def test_decorator_handles_no_args(self) -> None:
        @tool
        def get_status() -> str:
            """Return current status."""
            return "ok"

        schema = get_status.to_json_schema()
        assert "parameters" in schema["function"]
        assert get_status.fn() == "ok"


# ------------------------------------------------------------------
# ToolDispatcher - uses str args that the tool accepts
# ------------------------------------------------------------------


@pytest.fixture
def dispatcher() -> ToolDispatcher:
    @tool
    def add(a: str, b: str) -> str:
        """Add two numbers."""
        return str(int(a) + int(b))

    @tool
    def subtract(a: str, b: str) -> str:
        """Subtract b from a."""
        return str(int(a) - int(b))

    return ToolDispatcher([add, subtract])


class TestToolDispatcher:
    """Tests for the ToolDispatcher class."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_schemas(self, dispatcher: ToolDispatcher) -> None:
        schemas = dispatcher.list_tools()
        assert len(schemas) == 2
        names = {s["function"]["name"] for s in schemas}
        assert names == {"add", "subtract"}

    @pytest.mark.asyncio
    async def test_execute_registered_tool(self, dispatcher: ToolDispatcher) -> None:
        result = await dispatcher.execute("add", {"a": "3", "b": "4"}, "tc1")
        assert result.content == "7"

    @pytest.mark.asyncio
    async def test_execute_unregistered_tool_raises(self, dispatcher: ToolDispatcher) -> None:
        with pytest.raises(Exception):
            await dispatcher.execute("unknown", {}, "tc1")

    @pytest.mark.asyncio
    async def test_execute_with_empty_args(self, dispatcher: ToolDispatcher) -> None:
        result = await dispatcher.execute("add", {}, "tc2")
        assert result.content == "0"

    @pytest.mark.asyncio
    async def test_result_includes_tool_call_id(self, dispatcher: ToolDispatcher) -> None:
        result = await dispatcher.execute("subtract", {"a": "10", "b": "3"}, "call-abc")
        assert result.tool_call_id == "call-abc"
        assert result.content == "7"

    @pytest.mark.asyncio
    async def test_empty_registry_raises_on_any_call(self) -> None:
        dispatcher = ToolDispatcher([])
        with pytest.raises(Exception):
            await dispatcher.execute("anything", {}, "x")
