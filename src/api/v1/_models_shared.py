"""Shared utilities for model management endpoints."""

from __future__ import annotations

from typing import Any


_download_progress: dict[str, dict] = {}


def _delete_all_models_of_type(model_type: str) -> None:
    """Delete all models of a given type (llm or embeddings) from disk and registry."""
    import shutil
    from pathlib import Path

    from src.api.dependencies import get_database_service, get_unified_registry
    from src.config.settings import LLM_DIR as llm_dir, EMBEDDINGS_DIR as emb_dir

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


def _validate_repo_id(repo_id: str) -> str | None:
    """Validate repo_id format. Returns error message or None if valid."""
    if (
        not repo_id
        or ".." in repo_id
        or repo_id.count("/") != 1
        or repo_id.startswith("/")
        or repo_id.endswith("/")
    ):
        return "Invalid repo_id"
    return None


def _validate_repo_id_simple(repo_id: str) -> str | None:
    """Validate repo_id without requiring org/name format. Returns error message or None."""
    if not repo_id or ".." in repo_id:
        return "Invalid repo_id"
    return None


def _delete_llm_model_file(repo_id: str, filename: str) -> dict[str, Any]:
    """Delete a single LLM model file from disk and registry.

    Returns a dict with either:
        {"success": True, "message": "..."}
        {"success": False, "error": "...", "status_code": int}
    """
    from pathlib import Path

    from src.api.dependencies import get_database_service, get_unified_registry
    from src.config.settings import LLM_DIR

    err = _validate_repo_id(repo_id)
    if err:
        return {"success": False, "error": err, "status_code": 400}

    db = get_database_service()
    reg = get_unified_registry()
    record = reg.get_llm(repo_id, db)
    if not record:
        return {"success": False, "error": f"Model {repo_id} not found", "status_code": 404}
    if filename not in record.get("files", {}):
        return {
            "success": False,
            "error": f"File {filename} not found in {repo_id}",
            "status_code": 404,
        }

    path = Path(record["files"][filename]["local_path"]).resolve()
    try:
        path.relative_to(Path(LLM_DIR).resolve())
    except ValueError:
        return {"success": False, "error": "Invalid file path", "status_code": 400}

    if path.exists():
        path.unlink()
        parent = path.parent
        while parent != Path(LLM_DIR).resolve() and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    del record["files"][filename]
    if record["files"]:
        reg._save(db)
    else:
        reg.remove_llm(repo_id, db)

    return {"success": True, "message": f"Deleted {repo_id}/{filename}"}


def _delete_embedding_model(repo_id: str) -> dict[str, Any]:
    """Delete an embedding model from disk and registry.

    Returns a dict with either:
        {"success": True, "message": "..."}
        {"success": False, "error": "...", "status_code": int}
    """
    import shutil
    from pathlib import Path

    from src.api.dependencies import get_database_service, get_unified_registry
    from src.config.settings import EMBEDDINGS_DIR

    err = _validate_repo_id_simple(repo_id)
    if err:
        return {"success": False, "error": err, "status_code": 400}

    db = get_database_service()
    reg = get_unified_registry()
    record = reg.get_embedding(repo_id, db)
    if not record:
        return {"success": False, "error": f"Model {repo_id} not found", "status_code": 404}

    local_path = record.get("local_path", "")
    if local_path:
        path = Path(local_path).resolve()
        try:
            path.relative_to(Path(EMBEDDINGS_DIR).resolve())
        except ValueError:
            return {"success": False, "error": "Invalid file path", "status_code": 400}

        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    reg.remove_embedding(repo_id, db)
    return {"success": True, "message": f"Deleted embedding {repo_id}"}
