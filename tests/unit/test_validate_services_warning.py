"""Tests for _validate_services warnings."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.main import _validate_services


class TestValidateServices:
    def test_warns_when_llama_base_url_empty(self, caplog) -> None:
        caplog.set_level("WARNING")
        mock_config = MagicMock()
        mock_config.llama_base_url = ""
        mock_config.qdrant_collection_name = "sigma_docs"
        with patch("src.config.settings.get_config", return_value=mock_config):
            _validate_services()
        assert any("llama_base_url missing" in msg for msg in caplog.messages)

    def test_warns_when_qdrant_collection_empty(self, caplog) -> None:
        caplog.set_level("WARNING")
        mock_config = MagicMock()
        mock_config.llama_base_url = "http://127.0.0.1:8080"
        mock_config.qdrant_collection_name = ""
        with patch("src.config.settings.get_config", return_value=mock_config):
            _validate_services()
        assert any("qdrant_collection_name missing" in msg for msg in caplog.messages)

    def test_no_warning_with_defaults(self, caplog) -> None:
        caplog.set_level("WARNING")
        mock_config = MagicMock()
        mock_config.llama_base_url = "http://127.0.0.1:8080"
        mock_config.qdrant_collection_name = "sigma_docs"
        with patch("src.config.settings.get_config", return_value=mock_config):
            _validate_services()
        warnings = [m for m in caplog.messages if "missing" in m]
        assert len(warnings) == 0
