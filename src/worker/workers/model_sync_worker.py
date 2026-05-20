import json
import logging
from pathlib import Path

from src.worker.base import BaseWorker

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path("data/models/registry.json")


class ModelSyncWorker(BaseWorker):
    """Syncs LLM and embedding models from filesystem into a JSON registry.

    Avoids direct DuckDB access from the dispatcher thread to prevent
    native crashes. Saves to JSON file which gets synced to DB on next
    main-thread access.
    """

    async def process(self, task: dict) -> None:
        task_id = task.get("task_id", "")
        llm_dir = Path(task.get("llm_dir", "data/models/llm"))
        embeddings_dir = Path(task.get("embeddings_dir", "data/models/embeddings"))

        logger.info(
            f"[ModelSyncWorker] Starting model sync: LLM={llm_dir}, EMBEDDINGS={embeddings_dir}"
        )

        self.db.upsert_worker_state(
            worker_type="model_sync",
            status="running",
            current_task_id=task_id,
        )

        error_msg = ""
        try:
            registry = self._load_registry()

            logger.debug("[ModelSyncWorker] Scanning LLM folder...")
            self.db.update_worker_progress(
                worker_type="model_sync",
                progress_percent=0.0,
                current_file="scanning LLM models...",
            )
            self._scan_llm_folder(registry, llm_dir)

            self.db.update_worker_progress(
                worker_type="model_sync",
                progress_percent=50.0,
                current_file="LLM models scanned",
            )
            logger.debug("[ModelSyncWorker] LLM folder scanned.")

            logger.debug("[ModelSyncWorker] Scanning embeddings folder...")
            self._scan_embeddings_folder(registry, embeddings_dir)

            self.db.update_worker_progress(
                worker_type="model_sync",
                progress_percent=100.0,
                current_file="embeddings scanned",
            )
            logger.debug("[ModelSyncWorker] Embeddings folder scanned.")

            self._save_registry(registry)
            logger.info("[ModelSyncWorker] Registry saved to disk.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[ModelSyncWorker] Failed: {e}", exc_info=True)

        self.db.upsert_worker_state(
            worker_type="model_sync",
            status="idle",
            current_task_id="",
            error=error_msg,
        )
        logger.info(f"[ModelSyncWorker] Complete (error={error_msg or 'none'}).")

    def _load_registry(self) -> dict:
        if REGISTRY_PATH.exists():
            try:
                return json.loads(REGISTRY_PATH.read_text())
            except Exception:
                pass
        return {"llm": {}, "embeddings": {}}

    def _save_registry(self, registry: dict) -> None:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2))

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
