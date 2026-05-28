"""Shared utilities for model management endpoints."""

from __future__ import annotations


_download_progress: dict[str, dict] = {}


def _delete_all_models_of_type(model_type: str) -> None:
    """Delete all models of a given type (llm or embeddings) from disk and registry."""
    import shutil
    from pathlib import Path

    from src.api.dependencies import get_database_service, get_unified_registry
    from src.shared import LLM_DIR as llm_dir, EMBEDDINGS_DIR as emb_dir

    db = get_database_service()
    reg = get_unified_registry()
    models_dir = llm_dir if model_type == "llm" else emb_dir

    if model_type == "llm":
        reg.sync_llm_folder(models_dir, db)
        items = dict(reg.list_llms(db))
    else:
        reg.sync_embeddings_folder(models_dir, db)
        items = dict(reg.list_embeddings(db))

    for repo_id, data in items.items():
        if model_type == "llm":
            for filename, info in data.get("files", {}).items():
                path = Path(info["local_path"]).resolve()
                if path.exists():
                    path.unlink()
                parent = path.parent
                while (
                    parent != Path(models_dir).resolve()
                    and parent.exists()
                    and not any(parent.iterdir())
                ):
                    parent.rmdir()
                    parent = parent.parent
            reg.remove_llm(repo_id, db)
        else:
            path = Path(data["local_path"]).resolve()
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            reg.remove_embedding(repo_id, db)
