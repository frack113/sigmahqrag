"""Tests that llama.cpp uses the port from Config.llama_base_url."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


class TestLlamaPortFromConfig:
    @patch("src.infrastructure.llm.llamacpp.health.check_health")
    @patch("src.config.settings.get_config")
    async def test_health_check_skipped_when_not_autostart(
        self, mock_get_config: MagicMock, mock_check_health: AsyncMock
    ) -> None:
        mock_config = MagicMock()
        mock_config.service_is_autostart.return_value = False
        mock_config.llama_base_url = "http://127.0.0.1:9090"
        mock_get_config.return_value = mock_config

        from src.infrastructure.llm.llamacpp.auto_start import start_llamacpp

        await start_llamacpp()

        mock_check_health.assert_not_awaited()

    @patch("src.infrastructure.llm.llamacpp.health.check_health")
    @patch("src.infrastructure.llm.llamacpp.service.LlamaBinaryService")
    @patch("src.infrastructure.llm.llamacpp.auto_start._find_first_model")
    @patch("src.config.settings.get_config")
    async def test_service_start_uses_config_port(
        self,
        mock_get_config: MagicMock,
        mock_find_model: MagicMock,
        mock_service_cls: MagicMock,
        mock_check_health: AsyncMock,
    ) -> None:
        mock_config = MagicMock()
        mock_config.service_is_autostart.return_value = True
        mock_config.llama_base_url = "http://127.0.0.1:9090"
        mock_config.llama_binary_path = "C:\\fake\\bin"
        mock_get_config.return_value = mock_config
        mock_find_model.return_value = "C:\\fake\\model.gguf"

        mock_service = MagicMock()
        mock_service.start = AsyncMock(return_value={"success": True})
        mock_service_cls.return_value = mock_service

        mock_check_health.side_effect = [
            Exception("not running yet"),
            {"status": "active"},
        ]

        from src.infrastructure.llm.llamacpp.auto_start import start_llamacpp

        with patch("src.infrastructure.llm.llamacpp.auto_start.Path.exists", return_value=True):
            await start_llamacpp()

        actual_port = mock_service.start.call_args[1].get("port")
        assert actual_port == 9090, f"Expected port=9090, got {actual_port}"

    @patch("src.infrastructure.llm.llamacpp.health.check_health")
    @patch("src.config.settings.get_config")
    async def test_default_port_when_no_port_in_url(
        self, mock_get_config: MagicMock, mock_check_health: AsyncMock
    ) -> None:
        mock_config = MagicMock()
        mock_config.service_is_autostart.return_value = False
        mock_config.llama_base_url = "http://127.0.0.1"
        mock_get_config.return_value = mock_config

        from src.infrastructure.llm.llamacpp.auto_start import start_llamacpp

        await start_llamacpp()
