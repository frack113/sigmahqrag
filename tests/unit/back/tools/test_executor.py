"""Tests for the tool executor dispatch and error handling."""

import pytest

from src.back.tools.executor import ToolDispatcher, ToolExecutionError
from src.back.tools.registry import reset_tools, tool


class MockContext:
    pass


class TestToolDispatcherExecute:
    """Tests for ToolDispatcher.execute() method."""

    def setup_method(self) -> None:
        reset_tools()
        self.ctx = MockContext()

    @pytest.mark.asyncio
    async def test_execute_valid_tool(self) -> None:
        """Test executing a valid tool succeeds."""

        @tool
        async def greet(name: str) -> str:
            """Say hello.

            :param name: The name to greet.
            """
            return f"Hello, {name}!"

        dispatcher = ToolDispatcher([greet])
        result = await dispatcher.execute("greet", {"name": "World"}, "call_123")
        assert result.content == "Hello, World!"
        assert result.tool_call_id == "call_123"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises(self) -> None:
        """Test that executing an unknown tool raises ToolExecutionError."""
        dispatcher = ToolDispatcher([])

        with pytest.raises(ToolExecutionError) as exc_info:
            await dispatcher.execute("nonexistent", {}, "call_1")

        assert "Unknown tool 'nonexistent'" in str(exc_info.value)
        assert exc_info.value.tool_name == "nonexistent"

    @pytest.mark.asyncio
    async def test_execute_validation_error_wrapped(self) -> None:
        """Test that ValueError is wrapped in ToolExecutionError."""

        @tool
        async def validated_tool(field: str, value: str) -> str:
            """A tool with validation.

            :param field: The field name.
            :param value: The value.
            """
            valid_fields = {"author", "status"}
            if field not in valid_fields:
                raise ValueError(f"Invalid field '{field}'. Valid: {valid_fields}")
            return f"{field}={value}"

        dispatcher = ToolDispatcher([validated_tool])

        with pytest.raises(ToolExecutionError) as exc_info:
            await dispatcher.execute(
                "validated_tool",
                {"field": "invalid_field", "value": "x"},
                "call_2",
            )

        assert "Validation error" in str(exc_info.value)
        assert exc_info.value.tool_name == "validated_tool"

    @pytest.mark.asyncio
    async def test_execute_runtime_error_wrapped(self) -> None:
        """Test that generic exceptions are wrapped in ToolExecutionError."""

        @tool
        async def failing_tool() -> str:
            """A tool that always fails."""
            raise RuntimeError("Something went wrong")

        dispatcher = ToolDispatcher([failing_tool])

        with pytest.raises(ToolExecutionError) as exc_info:
            await dispatcher.execute("failing_tool", {}, "call_3")

        assert exc_info.value.tool_name == "failing_tool"

    @pytest.mark.asyncio
    async def test_execute_preserves_original_exception(self) -> None:
        """Test that the original exception is chained in ToolExecutionError."""

        @tool
        async def failing_tool() -> str:
            """A failing tool."""
            raise ValueError("original error")

        dispatcher = ToolDispatcher([failing_tool])

        with pytest.raises(ToolExecutionError) as exc_info:
            await dispatcher.execute("failing_tool", {}, "call_1")

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    @pytest.mark.asyncio
    async def test_execute_empty_args(self) -> None:
        """Test executing a tool with no required arguments."""

        @tool
        async def no_args() -> str:
            """A tool with no arguments."""
            return "done"

        dispatcher = ToolDispatcher([no_args])
        result = await dispatcher.execute("no_args", {}, "call_empty")
        assert result.content == "done"

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """Test executing a tool with required arguments."""

        @tool
        async def single_arg(x: int) -> str:
            """A single arg tool.

            :param x: An integer.
            """
            return str(x)

        dispatcher = ToolDispatcher([single_arg])
        result = await dispatcher.execute("single_arg", {"x": 42}, "call_4")
        assert result.content == "42"


class TestToolDispatcherRegister:
    """Tests for ToolDispatcher.register() method."""

    def setup_method(self) -> None:
        reset_tools()

    def test_register_tool_manually(self) -> None:
        """Test manually registering a tool via register()."""

        @tool
        async def manual_tool() -> str:
            """A manually registered tool."""
            return "manual"

        dispatcher = ToolDispatcher()
        dispatcher.register(manual_tool)
        tools = dispatcher.list_tools()
        assert len(tools) == 1

    def test_list_tools_returns_schemas(self) -> None:
        """Test that list_tools() returns OpenAI-compatible schemas."""

        @tool
        async def simple() -> str:
            """A simple tool."""
            return "ok"

        dispatcher = ToolDispatcher([simple])
        schemas = dispatcher.list_tools()

        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "simple"
        assert schema["function"]["description"] == "A simple tool."


class TestToolExecutionError:
    """Tests for ToolExecutionError exception class."""

    def test_error_has_tool_name(self) -> None:
        """Test that ToolExecutionError stores the tool name."""
        err = ToolExecutionError("test_tool", "Something failed")
        assert err.tool_name == "test_tool"

    def test_error_message_format(self) -> None:
        """Test the error message includes tool name and message."""
        err = ToolExecutionError("my_tool", "oops")
        expected = "Tool 'my_tool' failed: oops"
        assert str(err) == expected

    def test_error_inherits_from_exception(self) -> None:
        """Test that ToolExecutionError is a proper Exception subclass."""
        assert issubclass(ToolExecutionError, Exception)
