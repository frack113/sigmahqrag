"""Tests for ModelSyncWorker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.worker.workers.model_sync_worker import ModelSyncWorker


class TestModelSyncWorker:
    def _make_worker(self, mock_db: MagicMock) -> tuple[ModelSyncWorker, MagicMock]:
        mock_dispatcher = MagicMock()
        worker = ModelSyncWorker(mock_db, mock_dispatcher)
        return worker, mock_dispatcher

    def test_process_llm_and_embeddings(self, mock_db: MagicMock, tmp_path: Path) -> None:
        llm_dir = tmp_path / "models" / "llm"
        llm_dir.mkdir(parents=True)
        emb_dir = tmp_path / "models" / "embeddings"
        emb_dir.mkdir(parents=True)

        (tmp_path / "registry.json").write_text("{}")

        with (
            patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg,
            patch.object(ModelSyncWorker, "_scan_llm_folder") as mock_scan_llm,
            patch.object(ModelSyncWorker, "_scan_embeddings_folder") as mock_scan_emb,
            patch.object(ModelSyncWorker, "_save_registry") as mock_save,
        ):
            mock_cfg.return_value.paths_model_registry = str(tmp_path / "registry.json")
            mock_cfg.return_value.llm_dir = str(llm_dir)
            mock_cfg.return_value.embeddings_dir = str(emb_dir)

            worker, mock_dispatcher = self._make_worker(mock_db)
            worker.process({"task_id": "ms-1"})

        mock_scan_llm.assert_called_once()
        mock_scan_emb.assert_called_once()
        mock_save.assert_called_once()
        mock_dispatcher.update_worker_state.assert_called()

    def test_process_error_handling(self, mock_db: MagicMock, tmp_path: Path) -> None:
        with patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_model_registry = str(tmp_path / "registry.json")
            mock_cfg.return_value.llm_dir = "/nonexistent/llm"
            mock_cfg.return_value.embeddings_dir = "/nonexistent/embeddings"

            worker, mock_dispatcher = self._make_worker(mock_db)
            worker.process({"task_id": "ms-err"})

        calls = mock_dispatcher.update_worker_state.call_args_list
        last_call = calls[-1][1]
        assert last_call["status"].value == "idle"
        assert last_call["error"] == ""

    def test_load_registry_reads_existing(self, mock_db: MagicMock, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text('{"llm": {}, "embeddings": {}}')
        with patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_model_registry = str(reg)
            worker, _ = self._make_worker(mock_db)
            result = worker._load_registry()
            assert result == {"llm": {}, "embeddings": {}}

    def test_load_registry_returns_default_on_missing(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        with patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_model_registry = str(tmp_path / "nonexistent.json")
            worker, _ = self._make_worker(mock_db)
            result = worker._load_registry()
            assert result == {"llm": {}, "embeddings": {}}

    def test_load_registry_returns_default_on_corrupt(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text("{invalid json")
        with patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_model_registry = str(reg)
            worker, _ = self._make_worker(mock_db)
            result = worker._load_registry()
            assert result == {"llm": {}, "embeddings": {}}

    def test_save_registry_creates_file(self, mock_db: MagicMock, tmp_path: Path) -> None:
        reg = tmp_path / "sub" / "registry.json"
        with patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_model_registry = str(reg)
            worker, _ = self._make_worker(mock_db)
            worker._save_registry({"llm": {}, "embeddings": {}})
            assert reg.exists()
            assert "llm" in reg.read_text()

    def test_scan_llm_folder_skips_nonexistent(self, mock_db: MagicMock, tmp_path: Path) -> None:
        worker, _ = self._make_worker(mock_db)
        registry = {"llm": {}}
        worker._scan_llm_folder(registry, tmp_path / "nonexistent")
        assert registry == {"llm": {}}

    def test_scan_llm_folder_scans_gguf_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        model_sub = tmp_path / "org" / "model"
        model_sub.mkdir(parents=True)
        (model_sub / "file.gguf").write_bytes(b"fake gguf")
        (model_sub / "readme.md").write_text("readme")

        worker, _ = self._make_worker(mock_db)
        registry = {"llm": {}}
        worker._scan_llm_folder(registry, tmp_path)
        assert "org/model" in registry["llm"]
        assert "file.gguf" in registry["llm"]["org/model"]["files"]

    def test_scan_llm_folder_skips_cache_temp(self, mock_db: MagicMock, tmp_path: Path) -> None:
        for name in ("cache", "temp", ".hidden"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "file.gguf").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"llm": {}}
        worker._scan_llm_folder(registry, tmp_path)
        for name in ("cache", "temp", ".hidden"):
            assert name not in registry["llm"]

    def test_scan_llm_folder_skips_duplicate_repo_id(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        model_sub = tmp_path / "org" / "model"
        model_sub.mkdir(parents=True)
        (model_sub / "file.gguf").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"llm": {"org/model": {"existing": True}}}
        worker._scan_llm_folder(registry, tmp_path)
        assert registry["llm"]["org/model"] == {"existing": True}

    def test_scan_embeddings_folder_scans(self, mock_db: MagicMock, tmp_path: Path) -> None:
        emb_sub = tmp_path / "org" / "model"
        emb_sub.mkdir(parents=True)
        (emb_sub / "config.json").write_text("{}")

        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {}}
        worker._scan_embeddings_folder(registry, tmp_path)
        assert "org/model" in registry["embeddings"]

    def test_scan_embeddings_folder_skips_nonexistent(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {}}
        worker._scan_embeddings_folder(registry, tmp_path / "nonexistent")
        assert registry == {"embeddings": {}}

    def test_scan_embeddings_folder_skips_hidden(self, mock_db: MagicMock, tmp_path: Path) -> None:
        (tmp_path / ".hidden" / "sub").mkdir(parents=True)
        (tmp_path / ".hidden" / "sub" / "file.bin").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {}}
        worker._scan_embeddings_folder(registry, tmp_path)
        assert ".hidden" not in registry["embeddings"]

    def test_scan_embeddings_folder_skips_cache(self, mock_db: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "cache" / "sub").mkdir(parents=True)
        (tmp_path / "cache" / "sub" / "file.bin").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {}}
        worker._scan_embeddings_folder(registry, tmp_path)
        assert "cache" not in registry["embeddings"]

    def test_scan_embeddings_folder_skips_duplicate(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "org" / "model").mkdir(parents=True)
        (tmp_path / "org" / "model" / "file.bin").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {"org/model": {"existing": True}}}
        worker._scan_embeddings_folder(registry, tmp_path)
        assert registry["embeddings"]["org/model"] == {"existing": True}

    def test_scan_llm_folder_skips_sub_cache_temp(self, mock_db: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "org" / "temp").mkdir(parents=True)
        (tmp_path / "org" / "temp" / "f.gguf").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"llm": {}}
        worker._scan_llm_folder(registry, tmp_path)
        assert "org/temp" not in registry["llm"]

    def test_scan_llm_folder_skips_sub_hidden(self, mock_db: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "org" / ".hidden").mkdir(parents=True)
        (tmp_path / "org" / ".hidden" / "f.gguf").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"llm": {}}
        worker._scan_llm_folder(registry, tmp_path)
        assert "org/.hidden" not in registry["llm"]

    def test_scan_embeddings_folder_skips_sub_cache_temp(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "org" / "cache").mkdir(parents=True)
        (tmp_path / "org" / "cache" / "f.bin").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {}}
        worker._scan_embeddings_folder(registry, tmp_path)
        assert "org/cache" not in registry["embeddings"]

    def test_scan_embeddings_folder_skips_sub_hidden(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "org" / ".hidden").mkdir(parents=True)
        (tmp_path / "org" / ".hidden" / "f.bin").write_bytes(b"x")
        worker, _ = self._make_worker(mock_db)
        registry = {"embeddings": {}}
        worker._scan_embeddings_folder(registry, tmp_path)
        assert "org/.hidden" not in registry["embeddings"]

    def test_process_exception_in_try(self, mock_db: MagicMock, tmp_path: Path) -> None:
        with patch("src.worker.workers.model_sync_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_model_registry = str(tmp_path / "registry.json")
            mock_cfg.return_value.llm_dir = str(tmp_path)
            mock_cfg.return_value.embeddings_dir = str(tmp_path)
            worker, mock_dispatcher = self._make_worker(mock_db)
            with patch.object(worker, "_load_registry", side_effect=RuntimeError("load failed")):
                worker.process({"task_id": "ms-err2"})
        last_call = mock_dispatcher.update_worker_state.call_args_list[-1][1]
        assert last_call["error"] == "load failed"
