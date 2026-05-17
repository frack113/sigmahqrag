"""One-shot CLI to migrate existing JSON/TOML data into DuckDB.

Usage:
    uv run python scripts/migrate_to_duckdb.py
    uv run python scripts/migrate_to_duckdb.py --fail-after 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.back.database import DatabaseService

logger = logging.getLogger(__name__)

OLD_FILES: dict[str, Path] = {
    "embedding_config": Path("data/embedding.toml"),
    "system_prompts": Path("data/system_prompt.toml"),
    "models_llm": Path("data/models/registry.json"),
    "models_embeddings": Path("data/models/registry.json"),
    "embeddings_registry": Path("data/models/embeddings/embeddings_registry.json"),
    "doc_sigma_ref": Path("data/documents/sigmaref/registry.json"),
}

DATA_DIR = Path("data")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def _load_toml(path: Path) -> dict | None:
    try:
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error("Failed to load TOML %s: %s", path, e)
        return None


def _load_json(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        logger.warning("JSON %s is not a dict, skipping", path)
        return None
    except Exception as e:
        logger.error("Failed to load JSON %s: %s", path, e)
        return None


def _migrate_embedding_config(db: DatabaseService, fail_after: int) -> int:
    path = OLD_FILES["embedding_config"]
    if not path.exists():
        logger.info("Skipping embedding_config: %s not found", path)
        return 0
    data = _load_toml(path)
    if data is None:
        return 0
    count = 0
    for doc_type, cfg in data.items():
        if isinstance(cfg, dict):
            db.set_embedding_config(doc_type, cfg)
            count += 1
            if fail_after and count >= fail_after:
                raise RuntimeError(f"Injected failure after {count} items")
    return count


def _migrate_system_prompts(db: DatabaseService, fail_after: int) -> int:
    path = OLD_FILES["system_prompts"]
    if not path.exists():
        logger.info("Skipping system_prompts: %s not found", path)
        return 0
    data = _load_toml(path)
    if data is None:
        return 0
    prompts = data.get("prompts", {})
    count = 0
    for p_id, p_data in prompts.items():
        if isinstance(p_data, dict):
            row = {
                "id": p_data.get("id", p_id),
                "name": p_data.get("name", ""),
                "description": p_data.get("description", ""),
                "content": p_data.get("content", ""),
                "is_active": p_data.get("is_active", False),
            }
            db.upsert_prompt(row)
            count += 1
            if fail_after and count >= fail_after:
                raise RuntimeError(f"Injected failure after {count} items")
    return count


def _migrate_models(db: DatabaseService, fail_after: int) -> int:
    count = 0
    path = OLD_FILES["models_llm"]
    if path.exists():
        data = _load_json(path)
        if data:
            llms = data.get("llm", {})
            for repo_id, record in llms.items():
                if isinstance(record, dict):
                    entry = {
                        "repo_id": repo_id,
                        "model_type": "llm",
                        "local_path": record.get("local_path"),
                        "file_size": record.get("file_size", 0),
                        "files": record.get("files", {}),
                        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    db.upsert_model(entry)
                    count += 1
                    if fail_after and count >= fail_after:
                        raise RuntimeError(f"Injected failure after {count} items")

    path = OLD_FILES["embeddings_registry"]
    if path.exists():
        data = _load_json(path)
        if data:
            for repo_id, record in data.items():
                if isinstance(record, dict):
                    entry = {
                        "repo_id": repo_id,
                        "model_type": "embeddings",
                        "local_path": record.get("local_path"),
                        "file_size": record.get("file_size", 0),
                        "status": record.get("status", "ready"),
                        "dimension": record.get("dimension"),
                        "index_path": record.get("index_path"),
                        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    db.upsert_model(entry)
                    count += 1
                    if fail_after and count >= fail_after:
                        raise RuntimeError(f"Injected failure after {count} items")

    return count


def _migrate_doc_sigma_ref(db: DatabaseService, fail_after: int) -> int:
    path = OLD_FILES["doc_sigma_ref"]
    if not path.exists():
        logger.info("Skipping doc_sigma_ref: %s not found", path)
        return 0
    data = _load_json(path)
    if data is None:
        return 0
    count = 0
    for url_hash, entry in data.items():
        if isinstance(entry, dict):
            row = {
                "url_hash": url_hash,
                "original_url": entry.get("original_url", ""),
                "normalized_url": entry.get("normalized_url"),
                "content_type": entry.get("content_type"),
                "rule_id": entry.get("rule_id"),
                "title": entry.get("title"),
                "timestamp": entry.get("timestamp"),
                "content_sha256": entry.get("content_sha256"),
            }
            db.upsert_doc_sigma_ref(row)
            count += 1
            if fail_after and count >= fail_after:
                raise RuntimeError(f"Injected failure after {count} items")
    return count


def _check_old_files_exist() -> list[str]:
    found = []
    for _name, path in OLD_FILES.items():
        if path.exists():
            found.append(str(path))
    data_dirs = [
        DATA_DIR / "github",
        DATA_DIR / "github" / "repos",
    ]
    for d in data_dirs:
        if d.exists():
            found.append(str(d))
    return found


def main() -> None:
    _setup_logging()
    parser = argparse.ArgumentParser(description="Migrate JSON/TOML data to DuckDB")
    parser.add_argument(
        "--fail-after",
        type=int,
        default=0,
        help="Inject failure after processing N items (for testing rollback)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="DuckDB path (default: data/duckdb/sigmahq.duckdb)",
    )
    args = parser.parse_args()

    db = DatabaseService(db_path=args.db_path)
    db.initialize()

    total = 0
    try:
        total += _migrate_embedding_config(db, args.fail_after)
        total += _migrate_system_prompts(db, args.fail_after)
        total += _migrate_models(db, args.fail_after)
        total += _migrate_doc_sigma_ref(db, args.fail_after)
        logger.info("Migration complete: %d items migrated", total)
    except RuntimeError as e:
        logger.error("Migration aborted: %s", e)
        sys.exit(1)
    finally:
        db.close()

    old = _check_old_files_exist()
    if old:
        logger.info(
            "Old data files still present (%d found). They are no longer read by the app.",
            len(old),
        )


if __name__ == "__main__":
    main()
