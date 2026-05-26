"""Tests for embedding configuration."""

from unittest.mock import MagicMock, patch

from src.back.embedding_config import EmbeddingTypeConfig


class TestEmbeddingTypeConfig:
    def test_load(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {"model": "e5-small"}
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            result = config.load()
            assert result == {"model": "e5-small"}

    def test_load_empty(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {}
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            result = config.load()
            assert result == {}

    def test_save(self) -> None:
        mock_db = MagicMock()
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            result = config.save({"model": "e5-small"})
            assert result is True
            mock_db.set_embedding_config.assert_called_once_with("e5-small")

    def test_save_empty_model_deletes(self) -> None:
        mock_db = MagicMock()
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            result = config.save({"model": ""})
            assert result is True
            mock_db.delete_embedding_config.assert_called_once()

    def test_save_strips_model(self) -> None:
        mock_db = MagicMock()
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            config.save({"model": "  e5-small  "})
            mock_db.set_embedding_config.assert_called_once_with("e5-small")

    def test_save_exception_returns_false(self) -> None:
        mock_db = MagicMock()
        mock_db.set_embedding_config.side_effect = RuntimeError("db error")
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            result = config.save({"model": "e5-small"})
            assert result is False

    def test_update_type(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {"model": "e5-small"}
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            result = config.update_type("global", {"model": "e5-large"})
            mock_db.set_embedding_config.assert_called_once_with("e5-large")
            assert result == {"model": "e5-small"}

    def test_update_type_empty_model_deletes(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {}
        config = EmbeddingTypeConfig()
        with patch("src.back.database.DatabaseService.get_instance", return_value=mock_db):
            config.update_type("global", {"model": ""})
            mock_db.delete_embedding_config.assert_called_once()
