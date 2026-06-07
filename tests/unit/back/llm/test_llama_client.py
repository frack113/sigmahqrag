"""Tests for LlamaClient OpenAILike integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.llm.llamacpp.client import LlamaClient


class TestLlamaClientInit:
    def test_default_base_url(self) -> None:
        with patch(
            "src.infrastructure.llm.llamacpp.client._default_base_url",
            return_value="http://test:8080",
        ):
            client = LlamaClient()
            assert client.base_url == "http://test:8080"

    def test_custom_base_url(self) -> None:
        client = LlamaClient("http://custom:9999")
        assert client.base_url == "http://custom:9999"

    def test_trailing_slash_stripped(self) -> None:
        with patch(
            "src.infrastructure.llm.llamacpp.client._default_base_url",
            return_value="http://test:8080/",
        ):
            client = LlamaClient()
            assert client.base_url == "http://test:8080"

    def test_openaillike_initialized(self) -> None:
        with patch(
            "src.infrastructure.llm.llamacpp.client._default_base_url",
            return_value="http://test:8080",
        ):
            client = LlamaClient()
            assert client._llm is not None


class TestLlamaClientGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_text(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.OpenAILike") as mock_llm_class,
        ):
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "Hello world"
            mock_instance.acomplete = AsyncMock(return_value=mock_resp)
            mock_llm_class.return_value = mock_instance

            client = LlamaClient()
            result = await client.generate("test prompt")

            assert result == "Hello world"
            mock_instance.acomplete.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_stream_returns_chunks(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.OpenAILike") as mock_llm_class,
        ):
            mock_instance = MagicMock()

            async def stream_gen():
                r1 = MagicMock()
                r1.delta = "Hello"
                r2 = MagicMock()
                r2.delta = " world"
                yield r1
                yield r2

            mock_instance.astream_complete = AsyncMock(return_value=stream_gen())
            mock_llm_class.return_value = mock_instance

            client = LlamaClient()
            result = await client.generate("test prompt", stream=True)

            assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_handles_empty_response(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.OpenAILike") as mock_llm_class,
        ):
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = ""
            mock_instance.acomplete = AsyncMock(return_value=mock_resp)
            mock_llm_class.return_value = mock_instance

            client = LlamaClient()
            result = await client.generate("test prompt")

            assert result == ""


class TestLlamaClientChat:
    @pytest.mark.asyncio
    async def test_chat_returns_content(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.OpenAILike") as mock_llm_class,
        ):
            mock_instance = MagicMock()
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = "Assistant response"
            chat_resp = MagicMock()
            chat_resp.message = msg
            mock_instance.achat = AsyncMock(return_value=chat_resp)
            mock_llm_class.return_value = mock_instance

            client = LlamaClient()
            messages = [{"role": "user", "content": "Hello"}]
            result = await client.chat(messages)

            assert result == "Assistant response"

    @pytest.mark.asyncio
    async def test_chat_handles_empty_content(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.OpenAILike") as mock_llm_class,
        ):
            mock_instance = MagicMock()
            msg = MagicMock()
            msg.role = "assistant"
            msg.content = ""
            chat_resp = MagicMock()
            chat_resp.message = msg
            mock_instance.achat = AsyncMock(return_value=chat_resp)
            mock_llm_class.return_value = mock_instance

            client = LlamaClient()
            result = await client.chat([{"role": "user", "content": "Hello"}])

            assert result == ""


class TestLlamaClientChatRaw:
    @pytest.mark.asyncio
    async def test_chat_raw_returns_dict(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.OpenAILike") as mock_llm_class,
        ):
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.model_dump.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Response",
                            "tool_calls": [{"id": "1", "function": {"name": "test"}}],
                        }
                    }
                ]
            }
            mock_chat_ns = MagicMock()
            mock_chat_ns.create = AsyncMock(return_value=mock_response)
            mock_instance.async_openai_client = MagicMock()
            mock_instance.async_openai_client.chat = mock_chat_ns
            mock_llm_class.return_value = mock_instance

            client = LlamaClient()
            result = await client.chat_raw([{"role": "user", "content": "Hello"}])

            assert isinstance(result, dict)
            assert "choices" in result


class TestLlamaClientParseToolCalls:
    def test_valid_tool_calls(self) -> None:
        response = {
            "choices": [{"message": {"tool_calls": [{"id": "1", "function": {"name": "test"}}]}}]
        }
        result = LlamaClient.parse_tool_calls(response)
        assert len(result) == 1

    def test_no_choices(self) -> None:
        assert LlamaClient.parse_tool_calls({"choices": []}) == []

    def test_message_no_tool_calls(self) -> None:
        response = {"choices": [{"message": {}}]}
        assert LlamaClient.parse_tool_calls(response) == []


class TestLlamaClientEraseSlotCache:
    @pytest.mark.asyncio
    async def test_erase_slot_cache_success(self) -> None:
        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.httpx") as mock_httpx,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

            client = LlamaClient()
            result = await client.erase_slot_cache(0)

            assert result is True

    @pytest.mark.asyncio
    async def test_erase_slot_cache_connect_error(self) -> None:
        import httpx as real_httpx

        with (
            patch(
                "src.infrastructure.llm.llamacpp.client._default_base_url",
                return_value="http://test:8080",
            ),
            patch("src.infrastructure.llm.llamacpp.client.httpx") as mock_httpx,
        ):
            mock_client = AsyncMock()
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.ConnectError = real_httpx.ConnectError
            mock_client.post = AsyncMock(side_effect=real_httpx.ConnectError(""))

            client = LlamaClient()
            result = await client.erase_slot_cache(0)

            assert result is False
