"""Tests for the semantic query router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.router import (
    VALID_COLLECTIONS,
    _parse_llm_response,
    route_query,
)


class TestParseLlmResponse:
    def test_valid_single_collection(self) -> None:
        raw = '{"collections": ["sigma_rules"]}'
        assert _parse_llm_response(raw) == ["sigma_rules"]

    def test_valid_multiple_collections(self) -> None:
        raw = '{"collections": ["sigma_rules", "sigma_spec"]}'
        assert _parse_llm_response(raw) == ["sigma_rules", "sigma_spec"]

    def test_all_collections(self) -> None:
        raw = '{"collections": ["sigma_rules", "sigma_docs", "sigma_spec"]}'
        assert _parse_llm_response(raw) == ["sigma_rules", "sigma_docs", "sigma_spec"]

    def test_strips_markdown_fences(self) -> None:
        raw = '```json\n{"collections": ["sigma_docs"]}\n```'
        assert _parse_llm_response(raw) == ["sigma_docs"]

    def test_handles_extra_whitespace(self) -> None:
        raw = '  {"collections": ["sigma_spec"]}  '
        assert _parse_llm_response(raw) == ["sigma_spec"]

    def test_filters_invalid_collection_names(self) -> None:
        raw = '{"collections": ["sigma_rules", "invalid_collection"]}'
        assert _parse_llm_response(raw) == ["sigma_rules"]

    def test_empty_collections_list(self) -> None:
        raw = '{"collections": []}'
        assert _parse_llm_response(raw) == []

    def test_missing_collections_key(self) -> None:
        raw = '{"other_key": ["sigma_rules"]}'
        assert _parse_llm_response(raw) == []

    def test_non_list_collections(self) -> None:
        raw = '{"collections": "sigma_rules"}'
        assert _parse_llm_response(raw) == []

    def test_invalid_json(self) -> None:
        raw = "not json at all"
        assert _parse_llm_response(raw) == []

    def test_partial_json_with_surrounding_text(self) -> None:
        raw = 'Here is the classification: {"collections": ["sigma_docs"]} done.'
        assert _parse_llm_response(raw) == ["sigma_docs"]

    def test_trailing_comma(self) -> None:
        raw = '{"collections": ["sigma_rules",]}'
        result = _parse_llm_response(raw)
        assert result in (["sigma_rules"], [])


class TestRouteQuery:
    @pytest.mark.asyncio
    async def test_empty_query_returns_all(self) -> None:
        result = await route_query("")
        assert result == ["sigma_rules", "sigma_docs", "sigma_spec"]

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_all(self) -> None:
        result = await route_query("   ")
        assert result == ["sigma_rules", "sigma_docs", "sigma_spec"]

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_all(self) -> None:
        with (
            patch("src.rag.router.LlamaClient") as mock_llm_class,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_llm_class.return_value.base_url = "http://test:8080"
            mock_client_class.side_effect = Exception("connection refused")

            result = await route_query("test query")

        assert result == ["sigma_rules", "sigma_docs", "sigma_spec"]

    @pytest.mark.asyncio
    async def test_invalid_llm_output_falls_back_to_all(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"text": "I cannot classify this"}]}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with (
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.rag.router.LlamaClient") as mock_llm_class,
        ):
            mock_client_class.return_value.__aenter__.return_value = mock_http
            mock_client_class.return_value.__aexit__.return_value = None
            mock_llm_class.return_value.base_url = "http://test:8080"

            result = await route_query("test query")

        assert result == ["sigma_rules", "sigma_docs", "sigma_spec"]

    @pytest.mark.asyncio
    async def test_no_choices_falls_back_to_all(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)

        with (
            patch("httpx.AsyncClient") as mock_client_class,
            patch("src.rag.router.LlamaClient") as mock_llm_class,
        ):
            mock_client_class.return_value.__aenter__.return_value = mock_http
            mock_client_class.return_value.__aexit__.return_value = None
            mock_llm_class.return_value.base_url = "http://test:8080"

            result = await route_query("test query")

        assert result == ["sigma_rules", "sigma_docs", "sigma_spec"]


class TestValidCollections:
    def test_all_expected_collections(self) -> None:
        assert VALID_COLLECTIONS == {"sigma_rules", "sigma_docs", "sigma_spec"}
