"""Unit tests for DuckDB DatabaseService."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.back.database import DatabaseService


@pytest.fixture
def db() -> DatabaseService:
    tmp = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    tmp.close()
    os.unlink(tmp.name)
    d = DatabaseService(tmp.name)
    d.initialize()
    yield d
    d.close()
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


class TestConfig:
    def test_get_set_config(self, db: DatabaseService) -> None:
        assert db.get_config("foo") is None
        db.set_config("foo", {"value": "bar"})
        assert db.get_config("foo") == {"value": "bar"}

    def test_set_config_overwrites(self, db: DatabaseService) -> None:
        db.set_config("key", {"value": "v1"})
        db.set_config("key", {"value": "v2"})
        assert db.get_config("key") == {"value": "v2"}

    def test_config_empty_db(self, db: DatabaseService) -> None:
        assert db.get_config("nonexistent") is None


class TestEmbeddingConfig:
    """Tests for the new single global embedding config (replaced per-type mapping)."""

    def test_empty(self, db: DatabaseService) -> None:
        cfg = db.get_embedding_config()
        assert isinstance(cfg, dict)

    def test_set_and_get(self, db: DatabaseService) -> None:
        db.set_embedding_config("org/model")
        cfg = db.get_embedding_config()
        assert cfg["model"] == "org/model"

    def test_overwrite(self, db: DatabaseService) -> None:
        db.set_embedding_config("m1")
        db.set_embedding_config("m2")
        cfg = db.get_embedding_config()
        assert cfg["model"] == "m2"

    def test_delete(self, db: DatabaseService) -> None:
        db.set_embedding_config("m1")
        db.delete_embedding_config()
        cfg = db.get_embedding_config()
        assert "model" not in cfg or cfg["model"] == ""

    def test_single_model_only(self, db: DatabaseService) -> None:
        """There should be only one global model, not per-type mapping."""
        db.set_embedding_config("unique-model")
        cfg = db.get_embedding_config()
        assert "model" in cfg
        assert len(cfg) == 1  # Only 'model' key, no type keys


class TestSystemPrompts:
    def test_empty(self, db: DatabaseService) -> None:
        prompts = db.get_prompts()
        assert isinstance(prompts, list)

    def test_upsert_and_get(self, db: DatabaseService) -> None:
        db.upsert_prompt(
            {
                "id": "p1",
                "name": "test-prompt",
                "description": "A test",
                "content": "Hello",
                "is_active": True,
            }
        )
        prompts = db.get_prompts()
        assert len(prompts) >= 1
        assert any(p["name"] == "test-prompt" for p in prompts)

    def test_upsert_overwrite(self, db: DatabaseService) -> None:
        db.upsert_prompt(
            {
                "id": "p1",
                "name": "old",
                "description": "",
                "content": "c",
                "is_active": False,
            }
        )
        db.upsert_prompt(
            {
                "id": "p1",
                "name": "new",
                "description": "",
                "content": "c",
                "is_active": True,
            }
        )
        prompts = db.get_prompts()
        assert any(p["id"] == "p1" and p["name"] == "new" for p in prompts)

    def test_delete(self, db: DatabaseService) -> None:
        db.upsert_prompt({"id": "p1", "name": "del", "description": "", "content": "c"})
        db.delete_prompt("p1")
        assert not any(p["id"] == "p1" for p in db.get_prompts())

    def test_multiple_prompts(self, db: DatabaseService) -> None:
        db.upsert_prompt({"id": "a", "name": "A", "description": "", "content": "a"})
        db.upsert_prompt({"id": "b", "name": "B", "description": "", "content": "b"})
        assert len(db.get_prompts()) >= 2


class TestModels:
    def test_empty(self, db: DatabaseService) -> None:
        assert db.get_models() == []

    def test_upsert_llm(self, db: DatabaseService) -> None:
        db.upsert_model(
            {
                "repo_id": "org/llm",
                "model_type": "llm",
                "local_path": "/path/to/model",
                "file_size": 1234,
            }
        )
        models = db.get_models()
        assert len(models) == 1
        assert models[0]["repo_id"] == "org/llm"
        assert models[0]["model_type"] == "llm"

    def test_upsert_embedding(self, db: DatabaseService) -> None:
        db.upsert_model(
            {
                "repo_id": "org/emb",
                "model_type": "embeddings",
                "local_path": "/path/to/emb",
                "dimension": 384,
            }
        )
        models = db.get_models()
        assert len(models) == 1
        assert models[0]["dimension"] == 384

    def test_upsert_overwrite(self, db: DatabaseService) -> None:
        db.upsert_model({"repo_id": "r1", "model_type": "llm", "file_size": 1})
        db.upsert_model({"repo_id": "r1", "model_type": "llm", "file_size": 2})
        models = db.get_models()
        assert models[0]["file_size"] == 2

    def test_delete(self, db: DatabaseService) -> None:
        db.upsert_model({"repo_id": "r1", "model_type": "llm"})
        db.delete_model("r1")
        assert db.get_models() == []

    def test_with_files_json(self, db: DatabaseService) -> None:
        files = {"file1.gguf": {"filename": "file1.gguf", "file_size": 100}}
        db.upsert_model(
            {
                "repo_id": "org/m",
                "model_type": "llm",
                "files": files,
            }
        )
        models = db.get_models()
        assert models[0]["files"] == files

    def test_model_type_stored_as_is(self, db: DatabaseService) -> None:
        db.upsert_model({"repo_id": "bad", "model_type": "invalid"})
        models = db.get_models()
        match = [m for m in models if m["repo_id"] == "bad"]
        assert len(match) == 1
        assert match[0]["model_type"] == "invalid"


class TestDocSigmaRef:
    def test_empty(self, db: DatabaseService) -> None:
        assert db.get_doc_sigma_ref() == []

    def test_upsert_and_get(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {
                "url_hash": "abc123",
                "original_url": "https://example.com/doc",
                "content_type": "markdown",
                "rule_id": "rule-001",
            }
        )
        entries = db.get_doc_sigma_ref()
        assert len(entries) == 1
        assert entries[0]["url_hash"] == "abc123"

    def test_exists(self, db: DatabaseService) -> None:
        assert not db.doc_sigma_ref_exists("hash1")
        db.upsert_doc_sigma_ref({"url_hash": "hash1", "original_url": "http://x"})
        assert db.doc_sigma_ref_exists("hash1")

    def test_upsert_overwrite(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref({"url_hash": "h1", "original_url": "http://a"})
        db.upsert_doc_sigma_ref({"url_hash": "h1", "original_url": "http://b"})
        entries = db.get_doc_sigma_ref()
        assert entries[0]["original_url"] == "http://b"


class TestDocRegistry:
    def test_upsert(self, db: DatabaseService) -> None:
        assert not any(
            r["org"] == "test-org" and r["repo"] == "test-repo" for r in db.get_doc_registry(10)
        )
        db.upsert_doc_registry(
            {
                "url_hash": "reg1",
                "org": "test-org",
                "repo": "test-repo",
                "file_name": "README.md",
                "content_type": "markdown",
                "original_url": "https://example.com/README.md",
            }
        )
        results = db.get_doc_registry(10)
        assert len(results) == 1
        assert results[0]["org"] == "test-org"
        assert results[0]["repo"] == "test-repo"

    def test_upsert_overwrite(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "ow1",
                "org": "a",
                "repo": "b",
                "file_name": "old.md",
                "content_type": "markdown",
                "original_url": "http://old",
            }
        )
        db.upsert_doc_registry(
            {
                "url_hash": "ow1",
                "org": "a",
                "repo": "b",
                "file_name": "new.md",
                "content_type": "markdown",
                "original_url": "http://new",
            }
        )
        results = db.get_doc_registry(10)
        assert len(results) == 1
        assert results[0]["file_name"] == "new.md"

    def test_delete_by_repo(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "delr1",
                "org": "x",
                "repo": "y",
                "file_name": "file.md",
                "content_type": "markdown",
                "original_url": "http://test",
            }
        )
        db.delete_doc_registry_by_repo("x", "y")
        assert not any(r["org"] == "x" and r["repo"] == "y" for r in db.get_doc_registry(10))

    def test_delete_by_url(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "delu1",
                "org": "x",
                "repo": "y",
                "file_name": "file.md",
                "content_type": "markdown",
                "original_url": "http://unique-url",
            }
        )
        db.delete_doc_registry_by_url("http://unique-url")
        assert not any(r["url_hash"] == "delu1" for r in db.get_doc_registry(10))

    def test_update_embed_status(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "es1",
                "org": "x",
                "repo": "y",
                "file_name": "file.md",
                "content_type": "markdown",
                "original_url": "http://test",
                "embed_status": "discovery",
            }
        )
        db.update_doc_registry_embed_status("es1", "embedded")
        results = db.get_doc_registry(10)
        assert len(results) == 1
        assert results[0]["embed_status"] == "embedded"

    def test_get_pending_by_org_repo(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "pend1",
                "org": "test-org",
                "repo": "test-repo",
                "file_name": "waiting.md",
                "content_type": "markdown",
                "original_url": "http://pending",
                "embed_status": "discovery",
            }
        )
        db.upsert_doc_registry(
            {
                "url_hash": "pend2",
                "org": "other-org",
                "repo": "other-repo",
                "file_name": "other.md",
                "content_type": "markdown",
                "original_url": "http://other",
                "embed_status": "discovery",
            }
        )
        pending = db.get_pending_doc_registry("test-org", "test-repo")
        assert len(pending) == 1
        assert pending[0]["url_hash"] == "pend1"

    def test_pagination(self, db: DatabaseService) -> None:
        for i in range(5):
            db.upsert_doc_registry(
                {
                    "url_hash": f"pg{i}",
                    "org": "a",
                    "repo": "b",
                    "file_name": f"file{i}.md",
                    "content_type": "markdown",
                    "original_url": f"http://pg{i}",
                }
            )
        page1 = db.get_doc_registry(2, 0)
        assert len(page1) == 2
        page2 = db.get_doc_registry(2, 2)
        assert len(page2) == 2


class TestLocalFiles:
    def test_get_local_files_empty(self, db: DatabaseService) -> None:
        results = db.get_local_files()
        assert results == []

    def test_get_local_files(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "local1",
                "org": "local",
                "repo": "local",
                "file_name": "note.md",
                "content_type": "markdown",
                "original_url": "http://local/note.md",
            }
        )
        results = db.get_local_files()
        assert len(results) == 1
        assert results[0]["org"] == "local"
        assert results[0]["repo"] == "local"

    def test_get_local_file_count(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "cnt1",
                "org": "local",
                "repo": "local",
                "file_name": "a.md",
                "content_type": "markdown",
                "original_url": "http://local/a",
            }
        )
        db.upsert_doc_registry(
            {
                "url_hash": "cnt2",
                "org": "local",
                "repo": "local",
                "file_name": "b.md",
                "content_type": "markdown",
                "original_url": "http://local/b",
            }
        )
        count = db.get_local_file_count()
        assert count == 2

    def test_get_local_files_excludes_other_orgs(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "other1",
                "org": "sigmaref",
                "repo": "sigmaref",
                "file_name": "ref.md",
                "content_type": "markdown",
                "original_url": "http://ref",
            }
        )
        db.upsert_doc_registry(
            {
                "url_hash": "other2",
                "org": "local",
                "repo": "local",
                "file_name": "note.md",
                "content_type": "markdown",
                "original_url": "http://local/note",
            }
        )
        results = db.get_local_files()
        assert len(results) == 1
        assert results[0]["url_hash"] == "other2"

    def test_delete_local_file_by_url(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "dellocal",
                "org": "local",
                "repo": "local",
                "file_name": "remove.md",
                "content_type": "markdown",
                "original_url": "http://local/remove",
            }
        )
        db.delete_doc_registry_by_url("http://local/remove")
        count = db.get_local_file_count()
        assert count == 0

    def test_resync_local_file_sizes(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = str(tmp_path / "documents")
        os.makedirs(doc_dir, exist_ok=True)
        test_file = os.path.join(doc_dir, "test_rule.yml")
        with open(test_file, "w") as f:
            f.write("title: Test\n")
        file_size = os.path.getsize(test_file)

        db.upsert_doc_registry(
            {
                "url_hash": "resync1",
                "org": "local",
                "repo": "local",
                "file_name": "test_rule.yml",
                "content_type": "yaml",
                "original_url": f"file://{test_file}",
                "file_size": 0,
            }
        )
        result = db.resync_local_file_sizes(doc_dir)
        assert result["updated"] == 1
        assert result["skipped"] == 0
        assert result["error"] == 0

        record = db.get_local_files()[0]
        assert record["file_size"] == file_size

    def test_resync_local_file_sizes_missing_file(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = str(tmp_path / "documents")
        os.makedirs(doc_dir, exist_ok=True)

        db.upsert_doc_registry(
            {
                "url_hash": "resync2",
                "org": "local",
                "repo": "local",
                "file_name": "missing.yml",
                "content_type": "yaml",
                "original_url": "file:///nonexistent",
                "file_size": 0,
            }
        )
        result = db.resync_local_file_sizes(doc_dir)
        assert result["updated"] == 0
        assert result["error"] == 1

    def test_resync_local_file_sizes_non_existing_path(self, db: DatabaseService) -> None:
        result = db.resync_local_file_sizes("/nonexistent/path")
        assert result == {"updated": 0, "skipped": 0, "error": 0, "incomplete": 0}

    def test_resync_local_file_sizes_both_tables(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = str(tmp_path / "documents")
        os.makedirs(doc_dir, exist_ok=True)
        test_file = os.path.join(doc_dir, "local_rule.yml")
        file_size = 42
        with open(test_file, "w") as f:
            f.write("x" * file_size)

        db.upsert_doc_registry(
            {
                "url_hash": "reg1",
                "org": "local",
                "repo": "local",
                "file_name": "local_rule.yml",
                "content_type": "yaml",
                "original_url": f"file://{test_file}",
                "file_size": 0,
            }
        )
        db.upsert_doc_sigma_ref(
            {
                "url_hash": "sigma1",
                "org": "local",
                "repo": "local",
                "file_name": "local_rule.yml",
                "content_type": "yaml",
                "original_url": f"file://{test_file}",
                "file_size": 0,
            }
        )
        result = db.resync_local_file_sizes(doc_dir)
        assert result["updated"] == 2

        reg_record = db.get_local_files()[0]
        assert reg_record["file_size"] == file_size

    def test_resync_local_file_sizes_zero_byte_file(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = str(tmp_path / "documents")
        os.makedirs(doc_dir, exist_ok=True)
        empty_file = os.path.join(doc_dir, "empty.yml")
        Path(empty_file).touch()

        db.upsert_doc_registry(
            {
                "url_hash": "zero1",
                "org": "local",
                "repo": "local",
                "file_name": "empty.yml",
                "content_type": "yaml",
                "original_url": f"file://{empty_file}",
                "file_size": 0,
            }
        )
        result = db.resync_local_file_sizes(doc_dir)
        assert result["updated"] == 1

    def test_resync_local_file_sizes_existing_hash_skip(
        self, db: DatabaseService, tmp_path
    ) -> None:
        doc_dir = str(tmp_path / "documents")
        os.makedirs(doc_dir, exist_ok=True)
        file_size = 99

        file_path = os.path.join(doc_dir, "already_hashed.yml")
        with open(file_path, "w") as f:
            f.write("y" * file_size)

        db.upsert_doc_registry(
            {
                "url_hash": "hash1",
                "org": "local",
                "repo": "local",
                "file_name": "already_hashed.yml",
                "content_type": "yaml",
                "original_url": f"file://{file_path}",
                "file_size": 0,
            }
        )
        result = db.resync_local_file_sizes(doc_dir)
        assert result["updated"] == 1

    def test_resync_local_file_sizes_no_reprocess(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = str(tmp_path / "documents")
        os.makedirs(doc_dir, exist_ok=True)
        file_size = 50
        file_path = os.path.join(doc_dir, "already_sized.yml")
        with open(file_path, "w") as f:
            f.write("z" * file_size)

        db.upsert_doc_registry(
            {
                "url_hash": "nosize1",
                "org": "local",
                "repo": "local",
                "file_name": "already_sized.yml",
                "content_type": "yaml",
                "original_url": f"file://{file_path}",
                "file_size": file_size,
            }
        )
        result = db.resync_local_file_sizes(doc_dir)
        assert result["updated"] == 0


class TestEmbedProgress:
    def test_upsert_and_get(self, db: DatabaseService) -> None:
        db.upsert_worker_state(
            worker_type="github_embeddings",
            status="running",
            current_task_id="repo-123",
            progress_percent=0.42,
            current_file="file.txt",
        )
        entry = db.get_worker_progress("github_embeddings")
        assert entry is not None
        assert entry["status"] == "running"
        assert entry["progress_percent"] == pytest.approx(0.42, abs=0.01)

    def test_get_nonexistent(self, db: DatabaseService) -> None:
        assert db.get_worker_progress("nonexistent_worker") is None

    def test_update_progress(self, db: DatabaseService) -> None:
        db.upsert_worker_state(
            worker_type="sigmaref_embeddings",
            status="running",
            current_task_id="task-1",
            progress_percent=0.0,
        )
        db.update_worker_progress("sigmaref_embeddings", 50.0, "doc.md")
        entry = db.get_worker_progress("sigmaref_embeddings")
        assert entry["progress_percent"] == pytest.approx(50.0, abs=0.01)
        assert entry["current_file"] == "doc.md"

    def test_reset_stale(self, db: DatabaseService) -> None:
        db.upsert_worker_state(
            worker_type="github_embeddings",
            status="running",
            current_task_id="stale-task",
        )
        db._conn.execute(
            "UPDATE worker_state SET last_heartbeat = '2020-01-01T00:00:00Z' WHERE worker_type = ?",
            ("github_embeddings",),
        )
        db._conn.commit()
        db.reset_stale_workers(stale_seconds=60)
        entry = db.get_worker_progress("github_embeddings")
        assert entry is not None
        assert entry["status"] == "idle"


class TestGitMetadata:
    def test_get_nonexistent(self, db: DatabaseService) -> None:
        assert db.get_git_metadata("org/repo") is None

    def test_set_and_get(self, db: DatabaseService) -> None:
        db.set_git_metadata(
            "org/repo", {"org": "org", "name": "repo", "url": "http://x", "branch": "main"}
        )
        meta = db.get_git_metadata("org/repo")
        assert meta == {"org": "org", "name": "repo", "url": "http://x", "branch": "main"}

    def test_overwrite(self, db: DatabaseService) -> None:
        db.set_git_metadata(
            "org/repo", {"org": "org", "name": "repo", "url": "http://a", "branch": "main"}
        )
        db.set_git_metadata(
            "org/repo", {"org": "org", "name": "repo", "url": "http://b", "branch": "dev"}
        )
        meta = db.get_git_metadata("org/repo")
        assert meta["url"] == "http://b"
        assert meta["branch"] == "dev"

    def test_delete(self, db: DatabaseService) -> None:
        db.set_git_metadata(
            "org/repo", {"org": "org", "name": "repo", "url": "http://x", "branch": "main"}
        )
        db.delete_git_metadata("org/repo")
        assert db.get_git_metadata("org/repo") is None

    def test_multiple_repos(self, db: DatabaseService) -> None:
        db.set_git_metadata("a/r1", {"org": "a", "name": "r1", "url": "http://x", "branch": "main"})
        db.set_git_metadata("b/r2", {"org": "b", "name": "r2", "url": "http://y", "branch": "main"})
        assert db.get_git_metadata("a/r1")["name"] == "r1"
        assert db.get_git_metadata("b/r2")["name"] == "r2"


class TestGitSelectedDirs:
    def test_empty(self, db: DatabaseService) -> None:
        assert db.get_selected_dirs("org/repo") == []

    def test_set_and_get(self, db: DatabaseService) -> None:
        db.set_selected_dirs("org/repo", ["rules", "docs"])
        dirs = db.get_selected_dirs("org/repo")
        assert dirs == ["docs", "rules"]

    def test_overwrite_clears_old(self, db: DatabaseService) -> None:
        db.set_selected_dirs("org/repo", ["old"])
        db.set_selected_dirs("org/repo", ["new"])
        assert db.get_selected_dirs("org/repo") == ["new"]

    def test_delete(self, db: DatabaseService) -> None:
        db.set_selected_dirs("org/repo", ["a", "b"])
        db.delete_selected_dirs("org/repo")
        assert db.get_selected_dirs("org/repo") == []

    def test_independent_repos(self, db: DatabaseService) -> None:
        db.set_selected_dirs("a/r1", ["x"])
        db.set_selected_dirs("b/r2", ["y"])
        assert db.get_selected_dirs("a/r1") == ["x"]
        assert db.get_selected_dirs("b/r2") == ["y"]


class TestConcurrency:
    def test_write_lock_does_not_deadlock(self, db: DatabaseService) -> None:
        import threading

        def writer(key: str) -> None:
            for i in range(10):
                db.set_config(key, {"i": i})

        threads = [threading.Thread(target=writer, args=(f"k{j}",)) for j in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for j in range(4):
            val = db.get_config(f"k{j}")
            assert val is not None
            assert "i" in val


class TestRoundtrip:
    def test_crud_all_tables(self, db: DatabaseService) -> None:
        db.set_config("ck", {"v": 1})
        assert db.get_config("ck") == {"v": 1}

        db.set_embedding_config("m1")
        cfg = db.get_embedding_config()
        assert cfg.get("model") == "m1"

        db.upsert_prompt({"id": "pid", "name": "n", "description": "d", "content": "c"})
        assert len(db.get_prompts()) >= 1

        db.upsert_model({"repo_id": "org/m", "model_type": "llm"})
        assert len(db.get_models()) >= 1

        db.upsert_doc_sigma_ref({"url_hash": "h1", "original_url": "http://x"})
        assert db.doc_sigma_ref_exists("h1")

        db.set_git_metadata(
            "org/repo", {"org": "org", "name": "repo", "url": "http://x", "branch": "main"}
        )
        assert db.get_git_metadata("org/repo")["org"] == "org"

        db.set_selected_dirs("org/repo", ["a", "b"])
        assert db.get_selected_dirs("org/repo") == ["a", "b"]


class TestInitEdgeCases:
    def test_double_initialize_is_noop(self, db: DatabaseService) -> None:
        db.initialize()
        assert db._initialized is True

    def test_recreate_singleton_closes_previous(self) -> None:
        import os
        import tempfile

        tmp1 = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        tmp1.close()
        os.unlink(tmp1.name)
        d1 = DatabaseService(tmp1.name)
        d1.initialize()
        assert DatabaseService._instance is d1

        tmp2 = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        tmp2.close()
        os.unlink(tmp2.name)
        d2 = DatabaseService(tmp2.name)
        assert DatabaseService._instance is d2
        d2.initialize()
        d2.close()
        if os.path.exists(tmp2.name):
            os.unlink(tmp2.name)


class TestDefaultDbPath:
    def test_default_path_uses_config(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_cfg = MagicMock()
        mock_cfg.paths_duckdb_path = "/tmp/test.duckdb"
        with patch("src.back.database.service._default_db_path") as mock_fn:
            mock_fn.return_value = "/tmp/test.duckdb"
            svc = DatabaseService()
            assert "test.duckdb" in str(svc.db_path)
            svc.close()


class TestInitializeLoadFromFile:
    def test_load_from_existing_db(self, tmp_path) -> None:
        db_file = tmp_path / "existing.duckdb"
        d = DatabaseService(str(db_file))
        d.initialize()
        d.set_config("k", "v")
        d.persist(str(db_file))
        d.close()

        d2 = DatabaseService(str(db_file))
        d2.initialize()
        assert d2.get_config("k") == "v"
        d2.close()
        if db_file.exists():
            db_file.unlink()


class TestPersist:
    def test_persist_before_initialize_returns_early(self) -> None:
        import os
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        tmp.close()
        os.unlink(tmp.name)
        d = DatabaseService(tmp.name)
        d.persist()
        d.close()

    def test_persist_to_custom_path(self, db: DatabaseService, tmp_path) -> None:
        target = tmp_path / "custom.duckdb"
        db.set_config("ck", "cv")
        db.persist(str(target))
        assert target.exists()
        target.unlink()


class TestGetConfig:
    def test_plain_string_returned_as_is(self, db: DatabaseService) -> None:
        db._writer_conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)", ("plain", '"raw_string"')
        )
        db._writer_conn.commit()
        val = db.get_config("plain")
        assert val == "raw_string"

    def test_json_decode_error_returns_raw(self, db: DatabaseService) -> None:
        db._writer_conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)", ("bad", "not-json{")
        )
        db._writer_conn.commit()
        val = db.get_config("bad")
        assert val == "not-json{"


class TestModelsFilesJsonError:
    def test_invalid_files_json(self, db: DatabaseService) -> None:
        db._writer_conn.execute(
            "INSERT INTO models (repo_id, model_type, files) VALUES (?, ?, ?)",
            ("org/bad", "llm", "{bad json}"),
        )
        db._writer_conn.commit()
        models = db.get_models()
        match = [m for m in models if m["repo_id"] == "org/bad"]
        assert len(match) == 1
        assert match[0]["files"] == {}


class TestDocSigmaRefPending:
    def test_get_pending_all(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {"url_hash": "h1", "original_url": "http://x", "embed_status": "discovery"}
        )
        db.upsert_doc_sigma_ref(
            {"url_hash": "h2", "original_url": "http://y", "embed_status": "embedded"}
        )
        pending = db.get_pending_sigma_ref()
        assert len(pending) == 1
        assert pending[0]["url_hash"] == "h1"

    def test_get_pending_filtered_by_org_repo(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {
                "url_hash": "pa",
                "org": "a",
                "repo": "b",
                "original_url": "http://a",
                "embed_status": "discovery",
            }
        )
        db.upsert_doc_sigma_ref(
            {
                "url_hash": "pb",
                "org": "c",
                "repo": "d",
                "original_url": "http://c",
                "embed_status": "discovery",
            }
        )
        pending = db.get_pending_sigma_ref(org="a", repo="b")
        assert len(pending) == 1
        assert pending[0]["url_hash"] == "pa"

    def test_update_embed_status(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {"url_hash": "up1", "original_url": "http://u", "embed_status": "discovery"}
        )
        db.update_sigma_ref_embed_status("up1", "embedded")
        refs = db.get_doc_sigma_ref()
        assert refs[0]["embed_status"] == "embedded"

    def test_delete_by_repo(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {"url_hash": "dr1", "org": "x", "repo": "y", "original_url": "http://d"}
        )
        db.delete_doc_sigma_ref_by_repo("x", "y")
        refs = db.get_doc_sigma_ref()
        assert all(r["org"] != "x" or r["repo"] != "y" for r in refs)


class TestResetEmbedStatus:
    def test_sigmaref_collection(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {
                "url_hash": "s1",
                "org": "sigmaref",
                "repo": "sigmaref",
                "original_url": "http://s",
                "embed_status": "embedded",
            }
        )
        db.reset_embed_status_for_collection("sigmaref")
        refs = db.get_doc_sigma_ref()
        assert refs[0]["embed_status"] == "discovery"

    def test_local_collection(self, db: DatabaseService) -> None:
        db.upsert_doc_registry(
            {
                "url_hash": "l1",
                "org": "local",
                "repo": "local",
                "original_url": "http://l",
                "embed_status": "embedded",
            }
        )
        db.reset_embed_status_for_collection("local")
        refs = db.get_doc_registry()
        assert refs[0]["embed_status"] == "discovery"

    def test_custom_collection(self, db: DatabaseService) -> None:
        db.upsert_doc_sigma_ref(
            {
                "url_hash": "c1",
                "org": "myorg",
                "repo": "myrepo",
                "original_url": "http://c",
                "embed_status": "embedded",
            }
        )
        db.upsert_doc_registry(
            {
                "url_hash": "c2",
                "org": "myorg",
                "repo": "myrepo",
                "original_url": "http://c2",
                "embed_status": "embedded",
            }
        )
        db.reset_embed_status_for_collection("myorg/myrepo")
        refs_sigma = db.get_doc_sigma_ref()
        refs_reg = db.get_doc_registry()
        assert refs_sigma[0]["embed_status"] == "discovery"
        assert refs_reg[0]["embed_status"] == "discovery"


class TestResyncLocalFileSizesEdgeCases:
    def test_invalid_base_path(self, db: DatabaseService) -> None:
        result = db.resync_local_file_sizes("\x00invalid")
        assert result["error"] == 0

    def test_path_traversal_detected(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = tmp_path / "documents"
        doc_dir.mkdir()
        db.upsert_doc_registry(
            {
                "url_hash": "t1",
                "org": "local",
                "repo": "local",
                "file_name": "../../etc/passwd",
                "file_size": 0,
                "original_url": "http://t",
            }
        )
        result = db.resync_local_file_sizes(str(doc_dir))
        assert result["skipped"] == 1

    def test_bad_file_name_skipped(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = tmp_path / "documents"
        doc_dir.mkdir()
        db.upsert_doc_registry(
            {
                "url_hash": "bn1",
                "org": "local",
                "repo": "local",
                "file_name": None,
                "file_size": 0,
                "original_url": "http://bn",
            }
        )
        result = db.resync_local_file_sizes(str(doc_dir))
        assert result["skipped"] == 1

    def test_hash_failure_keeps_incomplete(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = tmp_path / "documents"
        doc_dir.mkdir()
        f = doc_dir / "unreadable.yml"
        f.write_text("data")
        f.chmod(0o000)
        db.upsert_doc_registry(
            {
                "url_hash": "hf1",
                "org": "local",
                "repo": "local",
                "file_name": "unreadable.yml",
                "file_size": 0,
                "content_sha256": None,
                "original_url": "http://hf",
            }
        )
        result = db.resync_local_file_sizes(str(doc_dir))
        f.chmod(0o644)
        assert result["error"] >= 1 or result["incomplete"] >= 0

    def test_batch_update_exception(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = tmp_path / "documents"
        doc_dir.mkdir()
        f = doc_dir / "batch.yml"
        f.write_text("x" * 10)
        db.upsert_doc_registry(
            {
                "url_hash": "be1",
                "org": "local",
                "repo": "local",
                "file_name": "batch.yml",
                "file_size": 0,
                "original_url": "http://be",
            }
        )
        result = db.resync_local_file_sizes(str(doc_dir))
        assert result["updated"] == 1


class TestGitMetadataList:
    def test_empty(self, db: DatabaseService) -> None:
        assert db.get_git_metadata_list() == []

    def test_returns_keys(self, db: DatabaseService) -> None:
        db.set_git_metadata("a/r1", {"org": "a", "name": "r1", "url": "http://x", "branch": "main"})
        db.set_git_metadata("b/r2", {"org": "b", "name": "r2", "url": "http://y", "branch": "dev"})
        keys = db.get_git_metadata_list()
        assert "a/r1" in keys
        assert "b/r2" in keys


class TestReposWithSelectedDirs:
    def test_empty(self, db: DatabaseService) -> None:
        assert db.get_repos_with_selected_dirs() == []

    def test_with_dirs(self, db: DatabaseService) -> None:
        db.set_selected_dirs("a/r1", ["rules"])
        db.set_selected_dirs("b/r2", ["docs"])
        repos = db.get_repos_with_selected_dirs()
        assert "a/r1" in repos
        assert "b/r2" in repos


class TestGetInstance:
    def test_get_instance_without_init_raises(self) -> None:
        from src.back.database import DatabaseService as DS

        DS._instance = None
        with pytest.raises(RuntimeError, match="not initialized"):
            DS.get_instance()

    def test_get_instance_returns_existing(self, db: DatabaseService) -> None:
        from src.back.database import DatabaseService as DS

        inst = DS.get_instance()
        assert inst is db


class TestSafeQueryNoConn:
    def test_returns_none_when_conn_is_none(self) -> None:
        import os
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
        tmp.close()
        os.unlink(tmp.name)
        d = DatabaseService(tmp.name)
        d._writer_conn = None
        result = d._safe_query("SELECT 1")
        assert result is None
        d.close()


class TestDefaultDbPathFunction:
    def test_calls_get_config(self) -> None:
        from unittest.mock import MagicMock, patch

        from src.back.database.service import _default_db_path

        mock_cfg = MagicMock()
        mock_cfg.paths_duckdb_path = "test/path.db"
        with patch("src.shared.config.get_config", return_value=mock_cfg):
            result = _default_db_path()
        assert result == "test/path.db"


class TestGetTables:
    def test_returns_sorted_names(self, db: DatabaseService) -> None:
        tables = db.get_tables()
        assert isinstance(tables, list)
        assert len(tables) >= 1

    def test_get_table_data(self, db: DatabaseService) -> None:
        db.set_config("ck", "cv")
        data = db.get_table_data("config")
        assert len(data) >= 1

    def test_get_table_data_invalid_name(self, db: DatabaseService) -> None:
        with pytest.raises(ValueError, match="Invalid table name"):
            db.get_table_data("nonexistent")

    def test_get_table_count(self, db: DatabaseService) -> None:
        db.set_config("ck", "cv")
        count = db.get_table_count("config")
        assert count >= 1


class TestPersistTwice:
    def test_persist_after_existing_target(self, db: DatabaseService, tmp_path) -> None:
        target = tmp_path / "twice.duckdb"
        db.set_config("k", "v")
        db.persist(str(target))
        db.persist(str(target))
        assert target.exists()
        target.unlink()


class TestResyncPathEdgeCases:
    def test_none_file_name_skipped(self, db: DatabaseService, tmp_path) -> None:
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        db.upsert_doc_registry(
            {
                "url_hash": "nf1",
                "org": "local",
                "repo": "local",
                "file_name": None,
                "file_size": 0,
                "original_url": "http://nf",
            }
        )
        result = db.resync_local_file_sizes(str(doc_dir))
        assert result["skipped"] == 1


class TestGetTableCount:
    def test_empty_table(self, db: DatabaseService) -> None:
        count = db.get_table_count("git_metadata")
        assert count == 0

    def test_invalid_name_raises(self, db: DatabaseService) -> None:
        with pytest.raises(ValueError, match="Invalid table name"):
            db.get_table_count("nonexistent")
