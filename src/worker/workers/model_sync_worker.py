import json
import logging
from pathlib import Path
from typing import Any

from src.config.settings import get_config
from src.worker.base import BaseWorker
from src.worker.enums import WorkerName, WorkerStatus

logger = logging.getLogger(__name__)


class ModelSyncWorker(BaseWorker):
    """Syncs LLM and embedding models from filesystem into a JSON registry.

    Avoids direct DuckDB access from the dispatcher thread to prevent
    native crashes. Saves to JSON file which gets synced to DB on next
    main-thread access.
    """

    def process(self, task: dict) -> None:
        assert self.dispatcher is not None
        task_id = task.get("task_id", "")
        cfg = get_config()
        llm_dir = Path(task.get("llm_dir", cfg.llm_dir))
        embeddings_dir = Path(task.get("embeddings_dir", cfg.embeddings_dir))

        logger.info(
            f"[ModelSyncWorker] Starting model sync: LLM={llm_dir}, EMBEDDINGS={embeddings_dir}"
        )

        self.dispatcher.update_worker_state(
            worker_type=WorkerName.MODEL_SYNC,
            status=WorkerStatus.RUNNING,
            current_task_id=task_id,
        )

        error_msg = ""
        try:
            registry = self._load_registry()

            logger.debug("[ModelSyncWorker] Scanning LLM folder...")
            self.dispatcher.update_worker_state(
                worker_type=WorkerName.MODEL_SYNC,
                progress_percent=0.0,
                current_file="scanning LLM models...",
            )
            self._scan_llm_folder(registry, llm_dir)

            self.dispatcher.update_worker_state(
                worker_type=WorkerName.MODEL_SYNC,
                progress_percent=50.0,
                current_file="LLM models scanned",
            )
            logger.debug("[ModelSyncWorker] LLM folder scanned.")

            logger.debug("[ModelSyncWorker] Scanning embeddings folder...")
            self._scan_embeddings_folder(registry, embeddings_dir)

            self.dispatcher.update_worker_state(
                worker_type=WorkerName.MODEL_SYNC,
                progress_percent=100.0,
                current_file="embeddings scanned",
            )
            logger.debug("[ModelSyncWorker] Embeddings folder scanned.")

            self._save_registry(registry)
            logger.info("[ModelSyncWorker] Registry saved to disk.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[ModelSyncWorker] Failed: {e}", exc_info=True)

        self.dispatcher.update_worker_state(
            worker_type=WorkerName.MODEL_SYNC,
            status=WorkerStatus.IDLE,
            current_task_id="",
            error=error_msg,
        )
        logger.info(f"[ModelSyncWorker] Complete (error={error_msg or 'none'}).")

    def _load_registry(self) -> dict[str, Any]:
        registry_path = Path(get_config().paths_model_registry)
        if registry_path.exists():
            try:
                return json.loads(registry_path.read_text())  # type: ignore[no-any-return]
            except Exception:
                pass
        return {"llm": {}, "embeddings": {}}

    def _save_registry(self, registry: dict) -> None:
        registry_path = Path(get_config().paths_model_registry)
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2))

    def _scan_llm_folder(self, registry: dict, llm_dir: Path) -> None:
        if not llm_dir.exists():
            return

        for model_dir in llm_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name.startswith("."):
                continue
            if model_dir.name in ("cache", "temp"):
                continue

            for sub_dir in model_dir.iterdir():
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue
                if sub_dir.name in ("cache", "temp"):
                    continue

                repo_id = f"{model_dir.name}/{sub_dir.name}"
                if repo_id in registry.get("llm", {}):
                    continue

                files = {}
                for f in sub_dir.rglob("*"):
                    if not f.is_file() or f.suffix != ".gguf" or f.name.startswith("."):
                        continue
                    size = f.stat().st_size
                    files[f.name] = {
                        "filename": f.name,
                        "local_path": str(f),
                        "file_size": size,
                        "status": "ready",
                    }

                if files:
                    registry.setdefault("llm", {})[repo_id] = {
                        "local_path": str(sub_dir),
                        "files": files,
                    }

    def _scan_embeddings_folder(self, registry: dict, embeddings_dir: Path) -> None:
        if not embeddings_dir.exists():
            return

        for model_dir in embeddings_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name.startswith("."):
                continue
            if model_dir.name in ("cache", "temp"):
                continue

            for sub_dir in model_dir.iterdir():
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue
                if sub_dir.name in ("cache", "temp"):
                    continue

                repo_id = f"{model_dir.name}/{sub_dir.name}"
                if repo_id in registry.get("embeddings", {}):
                    continue

                file_count = sum(1 for f in sub_dir.rglob("*") if f.is_file())
                if file_count > 0:
                    registry.setdefault("embeddings", {})[repo_id] = {
                        "local_path": str(sub_dir),
                    }
