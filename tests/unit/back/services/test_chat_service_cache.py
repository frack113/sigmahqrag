"""Tests for KV cache cleanup after translate in chat_service and translate endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from src.back.services.chat_service import ChatService


def _make_service() -> ChatService:
    with (
        patch("src.back.services.chat_service.SearchEngine"),
        patch("src.back.services.chat_service.RAGPipeline"),
        patch("src.back.services.chat_service.SigmaValidator"),
    ):
        svc = ChatService()
    svc.rag_pipeline.llm_client.erase_slot_cache = AsyncMock()
    return svc


class TestSearchCacheCleanup:
    async def test_erase_slot_cache_called_after_translate(self):
        svc = _make_service()
        message = "detection:\n  condition: selection\n  logsource: windows"

        with (
            patch("src.back.services.chat_service.detect_sigma_yaml", return_value=True),
            patch(
                "src.back.services.chat_service.extract_yaml_block",
                return_value="detection:\n  condition: selection",
            ),
            patch(
                "src.back.services.chat_service.translate_detection",
                new_callable=AsyncMock,
                return_value="Translated text",
            ),
            patch.object(svc.search_engine, "search", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc.rag_pipeline,
                "answer_search_query",
                new_callable=AsyncMock,
                return_value="Answer",
            ),
        ):
            result = await svc._handle_search(message)

        svc.rag_pipeline.llm_client.erase_slot_cache.assert_awaited_once()
        assert result == "Answer"

    async def test_erase_slot_cache_not_called_without_yaml(self):
        svc = _make_service()

        with (
            patch("src.back.services.chat_service.detect_sigma_yaml", return_value=False),
            patch.object(svc.search_engine, "search", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc.rag_pipeline,
                "answer_search_query",
                new_callable=AsyncMock,
                return_value="Answer",
            ),
        ):
            await svc._handle_search("simple question")

        svc.rag_pipeline.llm_client.erase_slot_cache.assert_not_awaited()

    async def test_erase_slot_cache_exception_does_not_break_flow(self):
        svc = _make_service()
        svc.rag_pipeline.llm_client.erase_slot_cache = AsyncMock(
            side_effect=RuntimeError("server down")
        )

        with (
            patch("src.back.services.chat_service.detect_sigma_yaml", return_value=True),
            patch(
                "src.back.services.chat_service.extract_yaml_block",
                return_value="detection:\n  condition: selection",
            ),
            patch(
                "src.back.services.chat_service.translate_detection",
                new_callable=AsyncMock,
                return_value="Translated text",
            ),
            patch.object(svc.search_engine, "search", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc.rag_pipeline,
                "answer_search_query",
                new_callable=AsyncMock,
                return_value="Answer",
            ),
        ):
            result = await svc._handle_search("detection:\n  condition: selection")

        assert result == "Answer"


class TestSearchStreamCacheCleanup:
    async def test_erase_slot_cache_called_after_translate_stream(self):
        svc = _make_service()
        message = "detection:\n  condition: selection\n  logsource: windows"

        async def fake_stream(*args: object, **kwargs: object):
            yield "token1"
            yield "token2"

        with (
            patch("src.back.services.chat_service.detect_sigma_yaml", return_value=True),
            patch(
                "src.back.services.chat_service.extract_yaml_block",
                return_value="detection:\n  condition: selection",
            ),
            patch(
                "src.back.services.chat_service.translate_detection",
                new_callable=AsyncMock,
                return_value="Translated text",
            ),
            patch.object(svc.search_engine, "search", new_callable=AsyncMock, return_value=[]),
            patch.object(
                svc.rag_pipeline,
                "answer_search_query_stream",
                side_effect=fake_stream,
            ),
        ):
            tokens = []
            async for t in svc._handle_search_stream(message):
                tokens.append(t)

        svc.rag_pipeline.llm_client.erase_slot_cache.assert_awaited_once()
        assert tokens == ["token1", "token2"]


class TestTranslateEndpointCacheCleanup:
    async def test_erase_slot_cache_called_in_endpoint(self):
        with (
            patch(
                "src.api.v1.translate.translate_detection", new_callable=AsyncMock
            ) as mock_translate,
            patch("src.api.v1.translate.RAGPipeline") as mock_rag_cls,
        ):
            mock_rag = MagicMock()
            mock_rag.llm_client.erase_slot_cache = AsyncMock()
            mock_rag_cls.return_value = mock_rag
            mock_translate.return_value = "Translated text"

            from fastapi.testclient import TestClient
            from fastapi import FastAPI
            from src.api.v1.translate import router

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.post(
                "/api/v1/translate/detection",
                json={"yaml": "detection:\n  condition: selection"},
            )
            assert response.status_code == 200
            mock_rag.llm_client.erase_slot_cache.assert_awaited_once()
