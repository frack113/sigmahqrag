"""Unit tests for UnifiedRegistry (model registry)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.back.models.registry import UnifiedRegistry


@pytest.fixture
def registry() -> UnifiedRegistry:
    UnifiedRegistry.reset_instance()
    return UnifiedRegistry.get_instance()


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.get_models.return_value = []
    return db


def _make_llm_dir(tmp_path: Path, org: str, model: str, *filenames: str) -> Path:
    """Create an LLM model directory with .gguf files under tmp_path."""
    model_dir = tmp_path / org / model
    model_dir.mkdir(parents=True)
    for name in filenames:
        (model_dir / name).write_text("x" * 100)
    return tmp_path


def _make_embedding_dir(tmp_path: Path, org: str, model: str, *filenames: str) -> Path:
    """Create an embedding model directory under tmp_path."""
    model_dir = tmp_path / org / model
    model_dir.mkdir(parents=True)
    for name in filenames:
        (model_dir / name).write_text("x" * 100)
    return tmp_path


# ── _save ─────────────────────────────────────────────────────────────────


class TestSave:
    def test_save_persists_files_for_llm(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        files = {"model.gguf": {"filename": "model.gguf", "file_size": 100}}
        registry._registry["llm"]["org/m"] = {
            "local_path": "/path",
            "file_size": 100,
            "status": "ready",
            "files": files,
        }
        registry._save(mock_db)

        mock_db.upsert_model.assert_called_once()
        args = mock_db.upsert_model.call_args[0][0]
        assert args["repo_id"] == "org/m"
        assert args["files"] == files
        assert "updated_at" in args
        assert args["updated_at"] is not None

    def test_save_persists_dimension_and_index_path_for_embeddings(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        registry._registry["embeddings"]["org/emb"] = {
            "local_path": "/path",
            "file_size": 0,
            "status": "ready",
            "dimension": 384,
            "index_path": "/path/index",
        }
        registry._save(mock_db)

        args = mock_db.upsert_model.call_args[0][0]
        assert args["dimension"] == 384
        assert args["index_path"] == "/path/index"
        assert "updated_at" in args

    def test_save_does_not_set_files_when_empty(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        registry._registry["llm"]["org/m"] = {
            "local_path": "/path",
            "file_size": 0,
            "status": "ready",
        }
        registry._save(mock_db)

        args = mock_db.upsert_model.call_args[0][0]
        assert "files" not in args or args["files"] is None


# ── sync_llm_folder ────────────────────────────────────────────────────────


class TestSyncLlmFolder:
    def test_discovers_gguf_files(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        _make_llm_dir(tmp_path, "LiquidAI", "LFM-1B", "model1.gguf", "model2.gguf")
        registry.sync_llm_folder(tmp_path, mock_db)

        assert "LiquidAI/LFM-1B" in registry._registry["llm"]
        entry = registry._registry["llm"]["LiquidAI/LFM-1B"]
        assert entry["status"] == "ready"
        assert entry["file_size"] == 200
        assert "model1.gguf" in entry["files"]
        assert "model2.gguf" in entry["files"]

    def test_skips_non_gguf_files(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        _make_llm_dir(tmp_path, "org", "m", "model.gguf", "readme.txt", "config.json")
        registry.sync_llm_folder(tmp_path, mock_db)

        entry = registry._registry["llm"]["org/m"]
        assert list(entry["files"].keys()) == ["model.gguf"]

    def test_skips_dot_directories(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        _make_llm_dir(tmp_path, "org", "m", "model.gguf")
        (tmp_path / ".cache").mkdir()
        (tmp_path / "org" / "m" / ".hidden").write_text("x")
        registry.sync_llm_folder(tmp_path, mock_db)

        assert "org/m" in registry._registry["llm"]

    def test_persists_to_db(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        _make_llm_dir(tmp_path, "org", "m", "model.gguf")
        registry.sync_llm_folder(tmp_path, mock_db)

        mock_db.upsert_model.assert_called_once()

    def test_updates_existing_entry_with_files_from_disk(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        registry._registry["llm"]["org/m"] = {
            "local_path": "/old",
            "file_size": 0,
            "status": "ready",
        }
        _make_llm_dir(tmp_path, "org", "m", "model.gguf")
        registry.sync_llm_folder(tmp_path, mock_db)

        entry = registry._registry["llm"]["org/m"]
        assert entry["file_size"] == 100
        assert "model.gguf" in entry["files"]

    def test_skips_cache_and_temp_dirs(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        for d in ("cache", "temp"):
            (tmp_path / d / "sub" / "model.gguf").mkdir(parents=True)
        registry.sync_llm_folder(tmp_path, mock_db)

        assert not registry._registry["llm"]

    def test_noop_when_dir_missing(self, registry: UnifiedRegistry, mock_db: MagicMock) -> None:
        registry.sync_llm_folder(Path("/nonexistent/path"), mock_db)
        registry._save(mock_db)
        mock_db.upsert_model.assert_not_called()


# ── sync_embeddings_folder ─────────────────────────────────────────────────


class TestSyncEmbeddingsFolder:
    def test_discovers_embedding_dirs(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        _make_embedding_dir(tmp_path, "org", "emb", "model.safetensors", "config.json")
        registry.sync_embeddings_folder(tmp_path, mock_db)

        assert "org/emb" in registry._registry["embeddings"]
        entry = registry._registry["embeddings"]["org/emb"]
        assert entry["status"] == "ready"
        assert entry["file_size"] > 0

    def test_preserves_dimension_and_index_path(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        registry._registry["embeddings"]["org/emb"] = {
            "local_path": "/old",
            "file_size": 0,
            "status": "ready",
            "dimension": 384,
            "index_path": "/path/to/index",
        }
        _make_embedding_dir(tmp_path, "org", "emb", "model.safetensors")
        registry.sync_embeddings_folder(tmp_path, mock_db)

        entry = registry._registry["embeddings"]["org/emb"]
        assert entry["dimension"] == 384
        assert entry["index_path"] == "/path/to/index"
        assert entry["file_size"] > 0

    def test_skips_cache_and_temp_dirs(
        self, registry: UnifiedRegistry, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        for d in ("cache", "temp"):
            (tmp_path / d / "sub" / "file.bin").mkdir(parents=True)
        registry.sync_embeddings_folder(tmp_path, mock_db)

        assert not registry._registry["embeddings"]

    def test_noop_when_dir_missing(self, registry: UnifiedRegistry, mock_db: MagicMock) -> None:
        registry.sync_embeddings_folder(Path("/nonexistent"), mock_db)
        mock_db.upsert_model.assert_not_called()


# ── delete / remove ────────────────────────────────────────────────────────


class TestRemove:
    def test_remove_llm_deletes_from_db(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        registry._registry["llm"]["org/m"] = {"local_path": "/p"}
        result = registry.remove_llm("org/m", mock_db)

        assert result is True
        mock_db.delete_model.assert_called_once_with("org/m")

    def test_remove_llm_returns_false_if_not_found(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        result = registry.remove_llm("nonexistent", mock_db)
        assert result is False
        mock_db.delete_model.assert_not_called()

    def test_remove_embedding_deletes_from_db(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        registry._registry["embeddings"]["org/emb"] = {"local_path": "/p"}
        result = registry.remove_embedding("org/emb", mock_db)

        assert result is True
        mock_db.delete_model.assert_called_once_with("org/emb")

    def test_remove_embedding_returns_false_if_not_found(
        self, registry: UnifiedRegistry, mock_db: MagicMock
    ) -> None:
        result = registry.remove_embedding("nonexistent", mock_db)
        assert result is False
        mock_db.delete_model.assert_not_called()
