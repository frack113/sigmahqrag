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
        assert db.get_embedding_config() == {}

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
        assert db.get_embedding_config() == {}

    def test_multiple_types(self, db: DatabaseService) -> None:
        db.set_embedding_config("a", {"model": "m1"})
        db.set_embedding_config("b", {"model": "m2"})
        cfg = db.get_embedding_config()
        assert set(cfg) == {"a", "b"}


class TestSystemPrompts:
    def test_empty(self, db: DatabaseService) -> None:
        assert db.get_prompts() == []

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
        assert len(prompts) == 1
        assert prompts[0]["name"] == "test-prompt"
        assert prompts[0]["is_active"] is True

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
        assert prompts[0]["name"] == "new"
        assert prompts[0]["is_active"] is True

    def test_delete(self, db: DatabaseService) -> None:
        db.upsert_prompt({"id": "p1", "name": "del", "description": "", "content": "c"})
        db.delete_prompt("p1")
        assert db.get_prompts() == []

    def test_multiple_prompts(self, db: DatabaseService) -> None:
        db.upsert_prompt({"id": "a", "name": "A", "description": "", "content": "a"})
        db.upsert_prompt({"id": "b", "name": "B", "description": "", "content": "b"})
        assert len(db.get_prompts()) == 2


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

    def test_model_type_constraint(self, db: DatabaseService) -> None:
        with pytest.raises(Exception, match="CHECK"):
            db.upsert_model({"repo_id": "bad", "model_type": "invalid"})


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


class TestEmbedProgress:
    def test_upsert_and_get(self, db: DatabaseService) -> None:
        db.upsert_embed_progress(
            "github",
            "repo-123",
            "running",
            0.42,
            "file.txt",
            None,
            "sigma_doc",
        )
        entry = db.get_embed_status("github", "repo-123")
        assert entry is not None
        assert entry["status"] == "running"
        assert entry["progress_percent"] == 0.42

    def test_get_nonexistent(self, db: DatabaseService) -> None:
        assert db.get_embed_status("github", "no-such-task") is None

    def test_running_tasks(self, db: DatabaseService) -> None:
        db.upsert_embed_progress("github", "t1", "running")
        db.upsert_embed_progress("github", "t2", "completed")
        active = db.get_active_embed_tasks()
        assert len(active) == 1
        assert active[0]["source_id"] == "t1"

    def test_reset_stale(self, db: DatabaseService) -> None:
        db.upsert_embed_progress("github", "stale", "running")
        db.reset_stale_embed_tasks()
        entry = db.get_embed_status("github", "stale")
        assert entry is not None
        assert entry["status"] == "failed"


class TestGitMetadata:
    def test_get_nonexistent(self, db: DatabaseService) -> None:
        assert db.get_git_metadata("org/repo") is None

    def test_set_and_get(self, db: DatabaseService) -> None:
        db.set_git_metadata("org/repo", {"key": "val", "number": 42})
        meta = db.get_git_metadata("org/repo")
        assert meta == {"key": "val", "number": 42}

    def test_overwrite(self, db: DatabaseService) -> None:
        db.set_git_metadata("org/repo", {"v": 1})
        db.set_git_metadata("org/repo", {"v": 2})
        assert db.get_git_metadata("org/repo") == {"v": 2}

    def test_delete(self, db: DatabaseService) -> None:
        db.set_git_metadata("org/repo", {"x": 1})
        db.delete_git_metadata("org/repo")
        assert db.get_git_metadata("org/repo") is None

    def test_multiple_repos(self, db: DatabaseService) -> None:
        db.set_git_metadata("a/r1", {"name": "r1"})
        db.set_git_metadata("b/r2", {"name": "r2"})
        assert db.get_git_metadata("a/r1") == {"name": "r1"}
        assert db.get_git_metadata("b/r2") == {"name": "r2"}


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
        assert len(db.get_prompts()) == 1

        db.upsert_model({"repo_id": "org/m", "model_type": "llm"})
        assert len(db.get_models()) == 1

        db.upsert_doc_sigma_ref({"url_hash": "h1", "original_url": "http://x"})
        assert db.doc_sigma_ref_exists("h1")

        db.set_git_metadata("org/repo", {"k": "v"})
        assert db.get_git_metadata("org/repo") == {"k": "v"}

        db.set_selected_dirs("org/repo", ["a", "b"])
        assert db.get_selected_dirs("org/repo") == ["a", "b"]
