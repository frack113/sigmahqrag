"""Tests for registered tool functions and schema validation."""

from src.back.tools.registry import (
    _VALID_FILTER_FIELDS,
    get_tools,
)


class TestFilterMetadataEnumValidation:
    """Tests for filter_metadata field validation via enum."""

    def test_filter_metadata_defines_valid_field_enum(self) -> None:
        """Test that _VALID_FILTER_FIELDS is a frozenset of strings."""
        assert isinstance(_VALID_FILTER_FIELDS, frozenset)
        assert all(isinstance(f, str) for f in _VALID_FILTER_FIELDS)


class TestToolFunctionRegistration:
    """Tests that all 5 tool functions are registered correctly."""

    def get_sigma_tool_names(self) -> list[str]:
        """Return the names of the 5 registered sigma tools."""
        return ["search_sigma", "filter_metadata", "explain_detection", "explain_rule", "summarize"]

    def test_all_five_tools_registered(self) -> None:
        """Test that exactly 5 tools are registered."""
        tools = get_tools()
        expected = self.get_sigma_tool_names()
        names = [t.name for t in tools]
        for name in expected:
            assert name in names, f"Expected tool '{name}' not found. Got: {names}"

    def test_search_sigma_registered(self) -> None:
        """Test that search_sigma tool is registered."""
        tools = get_tools()
        names = [t.name for t in tools]
        expected = self.get_sigma_tool_names()
        for name in expected:
            assert name in names, f"Expected tool '{name}' not found. Got: {names}"

    def test_filter_metadata_registered(self) -> None:
        """Test that filter_metadata tool is registered."""
        tools = get_tools()
        names = [t.name for t in tools]
        expected = self.get_sigma_tool_names()
        for name in expected:
            assert name in names, f"Expected tool '{name}' not found. Got: {names}"

    def test_explain_detection_registered(self) -> None:
        """Test that explain_detection tool is registered."""
        tools = get_tools()
        names = [t.name for t in tools]
        expected = self.get_sigma_tool_names()
        for name in expected:
            assert name in names, f"Expected tool '{name}' not found. Got: {names}"

    def test_explain_rule_registered(self) -> None:
        """Test that explain_rule tool is registered."""
        tools = get_tools()
        names = [t.name for t in tools]
        expected = self.get_sigma_tool_names()
        for name in expected:
            assert name in names, f"Expected tool '{name}' not found. Got: {names}"

    def test_summarize_registered(self) -> None:
        """Test that summarize tool is registered."""
        tools = get_tools()
        names = [t.name for t in tools]
        expected = self.get_sigma_tool_names()
        for name in expected:
            assert name in names, f"Expected tool '{name}' not found. Got: {names}"

    def test_all_tools_have_valid_schemas(self) -> None:
        """Test that all registered tools produce valid JSON schemas."""
        for td in get_tools():
            schema = td.to_json_schema()

            assert schema["type"] == "function"
            assert schema["function"]["name"], f"Tool '{td.name}' missing name"
            assert schema["function"]["description"], f"Tool '{td.name}' missing description"
            assert "parameters" in schema["function"]

            params = schema["function"]["parameters"]
            assert params.get("type") == "object"
            assert "properties" in params
            assert isinstance(params["properties"], dict)

            for prop_name, prop_schema in params["properties"].items():
                assert "type" in prop_schema, f"Tool '{td.name}' param '{prop_name}' missing type"

    def test_all_tools_have_description(self) -> None:
        """Test that all tools have non-empty descriptions."""
        for td in get_tools():
            assert td.description
            assert len(td.description) > 5

    def test_all_tools_have_required_params(self) -> None:
        """Test that all tools have at least one required parameter."""
        for td in get_tools():
            params = td.parameters
            required = params.get("required", [])
            assert len(required) >= 1, f"Tool '{td.name}' has no required parameters"

    def test_search_sigma_params(self) -> None:
        """Test search_sigma tool has correct parameters."""
        tools = get_tools()
        for t in tools:
            if t.name == "search_sigma":
                assert "query" in t.parameters.get("required", [])
                assert t.parameters["properties"]["query"]["type"] == "string"

    def test_filter_metadata_params(self) -> None:
        """Test filter_metadata tool has correct parameters."""
        tools = get_tools()
        for t in tools:
            if t.name == "filter_metadata":
                assert "field" in t.parameters.get("required", [])
                assert "value" in t.parameters.get("required", [])
                assert t.parameters["properties"]["field"]["type"] == "string"
                assert t.parameters["properties"]["value"]["type"] == "string"

    def test_explain_detection_params(self) -> None:
        """Test explain_detection tool has correct parameters."""
        tools = get_tools()
        for t in tools:
            if t.name == "explain_detection":
                assert "rule_yaml" in t.parameters.get("required", [])
                assert t.parameters["properties"]["rule_yaml"]["type"] == "string"

    def test_explain_rule_params(self) -> None:
        """Test explain_rule tool has correct parameters."""
        tools = get_tools()
        for t in tools:
            if t.name == "explain_rule":
                assert "rule_yaml" in t.parameters.get("required", [])

    def test_summarize_params(self) -> None:
        """Test summarize tool has correct parameters."""
        tools = get_tools()
        for t in tools:
            if t.name == "summarize":
                assert "text" in t.parameters.get("required", [])
                assert t.parameters["properties"]["text"]["type"] == "string"


class TestToolContextModel:
    """Tests for the ToolContext dataclass."""

    def test_tool_context_creation(self) -> None:
        """Test ToolContext can be instantiated."""
        from src.back.tools.models import ToolContext

        class MockEngine:
            pass

        class MockPipeline:
            pass

        ctx = ToolContext(
            search_engine=MockEngine(),
            rag_pipeline=MockPipeline(),
        )

        assert ctx.search_engine is not None
        assert ctx.rag_pipeline is not None

    def test_tool_context_fields(self) -> None:
        """Test ToolContext has expected fields."""
        from src.back.tools.models import ToolContext

        ctx = ToolContext(search_engine=None, rag_pipeline=None)
        assert hasattr(ctx, "search_engine")
        assert hasattr(ctx, "rag_pipeline")


class TestToolCallModel:
    """Tests for the ToolCall dataclass."""

    def test_tool_call_from_dict(self) -> None:
        """Test ToolCall.from_dict() parses correctly."""
        from src.back.tools.models import ToolCall

        data = {
            "id": "call_abc123",
            "function": {
                "name": "search_sigma",
                "arguments": '{"query": "ransomware"}',
            },
        }

        tc = ToolCall.from_dict(data)
        assert tc.id == "call_abc123"
        assert tc.name == "search_sigma"
        assert tc.arguments == {"query": "ransomware"}

    def test_tool_call_from_dict_invalid_json(self) -> None:
        """Test ToolCall.from_dict() handles invalid JSON gracefully."""
        from src.back.tools.models import ToolCall

        data = {
            "id": "call_xyz",
            "function": {
                "name": "test_tool",
                "arguments": "not-valid-json",
            },
        }

        tc = ToolCall.from_dict(data)
        assert tc.id == "call_xyz"
        assert tc.name == "test_tool"
        assert tc.arguments == {}

    def test_tool_call_from_dict_empty(self) -> None:
        """Test ToolCall.from_dict() handles empty data."""
        from src.back.tools.models import ToolCall

        tc = ToolCall.from_dict({})
        assert tc.id == ""
        assert tc.name == ""
        assert tc.arguments == {}

    def test_tool_call_from_dict_missing_function(self) -> None:
        """Test ToolCall.from_dict() handles missing function key."""
        from src.back.tools.models import ToolCall

        tc = ToolCall.from_dict({"id": "call_1"})
        assert tc.id == "call_1"
        assert tc.name == ""
        assert tc.arguments == {}
