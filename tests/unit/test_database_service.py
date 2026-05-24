"""Unit tests for DuckDB DatabaseService."""

from __future__ import annotations

import os
import tempfile

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
    def test_empty(self, db: DatabaseService) -> None:
        cfg = db.get_embedding_config()
        assert "markdown" in cfg

    def test_set_and_get(self, db: DatabaseService) -> None:
        db.set_embedding_config("markdown", {"model": "org/model", "chunk_size": 512})
        cfg = db.get_embedding_config()
        assert "markdown" in cfg
        assert cfg["markdown"]["model"] == "org/model"
        assert cfg["markdown"]["chunk_size"] == 512

    def test_overwrite(self, db: DatabaseService) -> None:
        db.set_embedding_config("markdown", {"model": "m1"})
        db.set_embedding_config("markdown", {"model": "m2"})
        cfg = db.get_embedding_config()
        assert cfg["markdown"]["model"] == "m2"

    def test_delete(self, db: DatabaseService) -> None:
        db.set_embedding_config("markdown", {"model": "m1"})
        db.delete_embedding_config("markdown")
        cfg = db.get_embedding_config()
        assert "markdown" not in cfg

    def test_multiple_types(self, db: DatabaseService) -> None:
        db.set_embedding_config("a", {"model": "m1"})
        db.set_embedding_config("b", {"model": "m2"})
        cfg = db.get_embedding_config()
        assert "a" in cfg
        assert "b" in cfg


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

        db.set_embedding_config("t1", {"model": "m1"})
        assert "t1" in db.get_embedding_config()

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
