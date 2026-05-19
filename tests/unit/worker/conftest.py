"""Shared fixtures for worker tests."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

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


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock DatabaseService for worker tests that don't need real DB."""
    db = MagicMock()
    db.upsert_worker_state = MagicMock()
    db.update_worker_progress = MagicMock()
    db.get_worker_progress = MagicMock(return_value=None)
    db.upsert_doc_registry = MagicMock()
    db.upsert_doc_sigma_ref = MagicMock()
    db.claim_task = MagicMock(return_value=True)
    db.is_worker_busy = MagicMock(return_value=False)
    db.reset_stale_workers = MagicMock()
    db.get_pending_sigma_ref = MagicMock(return_value=[])
    db.update_sigma_ref_embed_status = MagicMock()
    db.get_pending_doc_registry = MagicMock(return_value=[])
    db.update_doc_registry_embed_status = MagicMock()
    db.get_repos_with_selected_dirs = MagicMock(return_value=[])
    db.get_selected_dirs = MagicMock(return_value=[])
    return db


@pytest.fixture
def sample_task() -> dict:
    return {
        "task_id": "test-task-001",
        "task_type": "test",
        "collection_name": "test-org/test-repo",
        "source_type": "github",
    }


@pytest.fixture
def sample_sigmaref_task() -> dict:
    return {
        "task_id": "sigmaref-task-001",
        "task_type": "sigmaref_discovery",
        "collection_name": "sigmaref",
        "source_type": "sigmaref",
        "rules_dir": "data/rules",
        "output_dir": "data/documents/sigmaref",
    }


@pytest.fixture
def sample_github_discovery_task() -> dict:
    return {
        "task_id": "github-disc-001",
        "task_type": "github_discovery",
        "collection_name": "test-org/test-repo",
        "source_type": "github_discovery",
        "org": "test-org",
        "repo": "test-repo",
    }


@pytest.fixture
def sample_local_discovery_task() -> dict:
    return {
        "task_id": "local-disc-001",
        "task_type": "local_discovery",
        "collection_name": "local",
        "source_type": "local_discovery",
        "base_path": "data/documents/local",
    }


@pytest.fixture
def sample_sigmaref_embedding_task() -> dict:
    return {
        "task_id": "sigmaref-emb-001",
        "task_type": "sigmaref_embeddings",
        "collection_name": "sigmaref",
        "source_type": "sigmaref_embeddings",
        "registry_path": "data/documents/sigmaref",
    }


@pytest.fixture
def sample_github_embedding_task() -> dict:
    return {
        "task_id": "github-emb-001",
        "task_type": "github_embeddings",
        "collection_name": "test-org/test-repo",
        "source_type": "github_embeddings",
        "org": "test-org",
        "repo": "test-repo",
    }


@pytest.fixture
def sample_local_embedding_task() -> dict:
    return {
        "task_id": "local-emb-001",
        "task_type": "local_embeddings",
        "collection_name": "local",
        "source_type": "local_embeddings",
        "base_path": "data/documents/local",
    }
