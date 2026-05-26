"""Tests for chat mode schema."""

from src.shared.schemas.chat_mode import ChatMode


class TestChatMode:
    def test_search_value(self) -> None:
        assert ChatMode.SEARCH.value == "search"

    def test_explain_value(self) -> None:
        assert ChatMode.EXPLAIN.value == "explain"

    def test_coverage_value(self) -> None:
        assert ChatMode.COVERAGE.value == "coverage"

    def test_values_classmethod(self) -> None:
        result = ChatMode.values()
        assert "search" in result
        assert "explain" in result
        assert "coverage" in result
        assert len(result) == 3

    def test_from_string(self) -> None:
        assert ChatMode("search") == ChatMode.SEARCH
        assert ChatMode("explain") == ChatMode.EXPLAIN
        assert ChatMode("coverage") == ChatMode.COVERAGE

    def test_invalid_value_raises(self) -> None:
        try:
            ChatMode("invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
