"""Tests for the tool registry schema generation and validation."""

from src.back.tools.registry import (
    _enrich_enums,
    _VALID_FILTER_FIELDS,
    reset_tools,
    tool,
    get_tools,
    get_tool_by_name,
)


class TestToolDecoratorSchemaGeneration:
    """Tests for automatic JSON schema generation from function signatures."""

    def setup_method(self) -> None:
        """Reset tool registry before each test."""
        reset_tools()

    def test_simple_function_no_params(self) -> None:
        """Test schema generation for a function with no parameters."""

        @tool
        async def simple_tool() -> str:
            """A simple tool with no parameters."""
            return "result"

        tools = get_tools()
        assert len(tools) == 1
        assert tools[0].name == "simple_tool"
        assert tools[0].description == "A simple tool with no parameters."
        assert tools[0].parameters["properties"] == {}
        assert tools[0].parameters["required"] == []

    def test_function_with_string_param(self) -> None:
        """Test schema generation for a function with a string parameter."""

        @tool
        async def search_tool(query: str) -> str:
            """Search for something.

            :param query: The search query string.
            """
            return "results"

        schema = search_tool.parameters
        assert schema["properties"]["query"]["type"] == "string"
        assert schema["properties"]["query"]["description"] == "The search query string."
        assert "query" in schema["required"]

    def test_function_with_multiple_params(self) -> None:
        """Test schema generation for a function with multiple parameters."""

        @tool
        async def multi_param_tool(
            name: str,
            count: int,
        ) -> str:
            """A tool with multiple parameters.

            :param name: The name parameter.
            :param count: The count parameter.
            """
            return "result"

        schema = multi_param_tool.parameters
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["count"]["type"] == "integer"
        assert "name" in schema["required"]
        assert "count" in schema["required"]

    def test_function_with_optional_param(self) -> None:
        """Test schema generation for a function with an optional parameter."""
        from typing import Optional

        @tool
        async def optional_tool(
            required_field: str,
            optional_field: Optional[str] = None,
        ) -> str:
            """A tool with optional parameter.

            :param required_field: Required field.
            :param optional_field: Optional field.
            """
            return "result"

        schema = optional_tool.parameters
        assert "required_field" in schema["required"]
        assert "optional_field" not in schema["required"]

    def test_function_with_default_value(self) -> None:
        """Test schema generation for a function with default values."""

        @tool
        async def default_tool(
            name: str,
            count: int = 10,
        ) -> str:
            """A tool with defaults.

            :param name: The name.
            :param count: The count.
            """
            return "result"

        schema = default_tool.parameters
        assert "name" in schema["required"]
        assert "count" not in schema["required"]

    def test_function_without_annotation(self) -> None:
        """Test schema generation for a function with untyped parameters."""

        @tool
        async def untyped_tool(value) -> str:
            """A tool without type annotations.

            :param value: The value.
            """
            return "result"

        schema = untyped_tool.parameters
        assert schema["properties"]["value"]["type"] == "string"

    def test_function_without_docstring(self) -> None:
        """Test schema generation for a function without docstring."""
        from typing import Any

        @tool
        async def no_doc_tool(x: int) -> Any:
            return "result"

        schema = no_doc_tool.parameters
        assert schema["properties"]["x"]["type"] == "integer"
        assert "description" not in schema["properties"]["x"]

    def test_function_with_int_type(self) -> None:
        """Test integer type conversion."""

        @tool
        async def int_tool(count: int) -> str:
            return "result"

        schema = int_tool.parameters
        assert schema["properties"]["count"]["type"] == "integer"

    def test_function_with_float_type(self) -> None:
        """Test float/number type conversion."""

        @tool
        async def float_tool(ratio: float) -> str:
            return "result"

        schema = float_tool.parameters
        assert schema["properties"]["ratio"]["type"] == "number"

    def test_function_with_bool_type(self) -> None:
        """Test boolean type conversion."""

        @tool
        async def bool_tool(flag: bool) -> str:
            return "result"

        schema = bool_tool.parameters
        assert schema["properties"]["flag"]["type"] == "boolean"


class TestEnumEnrichment:
    """Tests for enum validation enrichment in schemas."""

    def test_enrich_enums_with_literal_type(self) -> None:
        """Test enum enrichment for Literal type parameters."""
        from typing import Literal
        import inspect

        sig = inspect.Signature(
            parameters=[
                inspect.Parameter(
                    "field",
                    inspect.Parameter.POSITIONAL_ONLY,
                    annotation=Literal["alpha", "beta", "gamma"],
                )
            ]
        )

        schema: dict = {"properties": {"field": {"type": "string"}}}
        _enrich_enums(sig, schema)

        assert schema["properties"]["field"].get("enum") == ["alpha", "beta", "gamma"]
        assert schema["properties"]["field"]["type"] == "string"

    def test_enrich_enums_skips_non_literal(self) -> None:
        """Test that non-Literal types are not enriched with enums."""
        import inspect

        sig = inspect.Signature(
            parameters=[
                inspect.Parameter("field", inspect.Parameter.POSITIONAL_ONLY, annotation=str)
            ]
        )

        schema: dict = {"properties": {"field": {"type": "string"}}}
        _enrich_enums(sig, schema)

        assert "enum" not in schema["properties"]["field"]


class TestToolRegistry:
    """Tests for tool registration and retrieval."""

    def setup_method(self) -> None:
        """Reset tool registry before each test."""
        reset_tools()

    def test_register_single_tool(self) -> None:
        """Test registering a single tool."""

        @tool
        async def my_tool() -> str:
            """A test tool."""
            return "hello"

        tools = get_tools()
        assert len(tools) == 1
        assert tools[0].name == "my_tool"

    def test_register_multiple_tools(self) -> None:
        """Test registering multiple tools."""

        @tool
        async def tool_one() -> str:
            """First tool."""
            return "1"

        @tool
        async def tool_two() -> str:
            """Second tool."""
            return "2"

        tools = get_tools()
        assert len(tools) == 2
        assert tools[0].name == "tool_one"
        assert tools[1].name == "tool_two"

    def test_get_tool_by_name(self) -> None:
        """Test finding a tool by name."""

        @tool
        async def findable_tool() -> str:
            """A findable tool."""
            return "found"

        found = get_tool_by_name("findable_tool")
        assert found is not None
        assert found.name == "findable_tool"

    def test_get_tool_by_name_not_found(self) -> None:
        """Test get_tool_by_name returns None for missing tool."""
        assert get_tool_by_name("nonexistent") is None

    def test_reset_tools_clears_registry(self) -> None:
        """Test that reset_tools clears all registered tools."""

        @tool
        async def temporary_tool() -> str:
            return "temp"

        assert len(get_tools()) == 1
        reset_tools()
        assert len(get_tools()) == 0

    def test_reset_tools_isolate(self) -> None:
        """Test that reset_tools isolates tests from each other."""

        @tool
        async def temp() -> str:
            return "x"

        reset_tools()
        assert len(get_tools()) == 0

    def test_tool_json_schema_output(self) -> None:
        """Test that ToolDef.to_json_schema() produces valid OpenAI format."""

        @tool
        async def schema_tool(query: str) -> str:
            """A tool for testing schemas.

            :param query: The query string.
            """
            return "result"

        schema = schema_tool.to_json_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "schema_tool"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["properties"]["query"]["type"] == "string"


class TestValidFilterFieldsConstant:
    """Tests for the _VALID_FILTER_FIELDS constant."""

    def test_valid_field_count(self) -> None:
        """Test that exactly 8 fields are defined."""
        assert len(_VALID_FILTER_FIELDS) == 8

    def test_contains_expected_fields(self) -> None:
        """Test that all expected filter fields are present."""
        expected_fields = {
            "author",
            "cve",
            "mitre",
            "level",
            "status",
            "logsource_product",
            "logsource_category",
            "source",
        }
        assert _VALID_FILTER_FIELDS == expected_fields

    def test_all_fields_are_strings(self) -> None:
        """Test that all valid filter fields are strings."""
        assert all(isinstance(f, str) for f in _VALID_FILTER_FIELDS)
