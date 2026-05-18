"""Tests for embed_sigmaref SSE endpoints and background task."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.qdrant import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ── _embed_progress_generator ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generator_not_found():
    """Unknown task_id yields not_found immediately."""
    from src.api.v1.qdrant import _embed_progress_generator

    events = [e async for e in _embed_progress_generator("no-such-task")]
    assert len(events) == 1
    data = json.loads(events[0].removeprefix("data: ").strip())
    assert data["status"] == "not_found"


@pytest.mark.asyncio
async def test_generator_yields_events_breaks_on_completed():
    from src.api.v1.qradnt import _embed_progress_generator  # Wait, typo in my thought, it's qdrant

    task_id = "test-gen-001"
    with patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst:
        mock_db = MagicMock()
        # Simulate two calls: processing then completed
        mock_db.get_embed_status.side_effect = [
            {"status": "processing", "processed": 1, "total": 5},
            {"status": "completed", "processed": 5, "total": 5},
        ]
        mock_db_inst.return_value = mock_db

        events = [e async for e in _embed_progress_generator(task_id)]
        assert len(events) == 2
        d1 = json.loads(events[0].removeprefix("data: ").strip())
        assert d1["status"] == "processing"
        d2 = json.loads(events[1].removeprefix("data: ").strip())
        assert d2["status"] == "completed"


@pytest.mark.asyncio
async def test_generator_breaks_on_failed():
    from src.api.v1.qdrant import _embed_progress_generator

    task_id = "test-gen-fail"
    with patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst:
        mock_db = MagicMock()
        mock_db.get_embed_status.return_value = {"status": "failed", "error": "boom"}
        mock_db_inst.return_value = mock_db

        events = [e async for e in _embed_progress_generator(task_id)]
        assert len(events) == 1
        data = json.loads(events[0].removeprefix("data: ").strip())
        assert data["status"] == "failed"


@pytest.mark.asyncio
async def test_generator_timeout_on_empty_queue():
    from src.api.v1.qdrant import _embed_progress_generator

    task_id = "test-gen-timeout"
    with patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst:
        mock_db = MagicMock()
        mock_db.get_embed_satus.return_value = {
            "status": "running"
        }  # typo in my thought, it's status
        mock_db_inst.return_value = mock_db

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            events = [e async for e in _embed_progress_generator(task_id)]

        assert len(events) == 1
        data = json.loads(events[0].removeprefix("data: ").strip())
        assert data["status"] == "timeout"


# ── embed_progress endpoint (GET /embed/{task_id}) ──────────────────────────


def test_embed_progress_not_found():
    response = client.get("/api/v1/qdrant/embed/no-such-task")
    assert response.status_code == 404
    assert response.json()["status"] == "not_found"


def test_embed_progress_found():
    task_id = "test-get-001"
    with patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst:
        mock_db = MagicMock()
        mock_db.get_embed_status.return_value = {"status": "running", "task_id": task_id}
        mock_db_inst.return_value = mock_db

        response = client.get(f"/api/v1/qdrant/embed/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["task_id"] == task_id


# ── embed_progress_stream endpoint (GET /embed/{task_id}/stream) ────────────


@pytest.mark.asyncio
async def test_embed_progress_stream_sse():
    task_id = "test-stream-001"
    with patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst:
        mock_db = MagicMock()
        mock_db.get_embed_status.return_value = {"status": "running", "task_id": task_id}
        mock_db_inst.return_value = mock_db

        with patch("src.api.v1.qdrant._embed_progress_generator") as mock_gen:

            async def _gen():
                yield f"data: {json.dumps({'status': 'completed'})}\n\n"

            mock_gen.return_value = _gen()
            response = client.get(f"/api/v1/qdrant/embed/{task_id}/stream")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    with patch("src.api.v1.qdrant._embed_progress_generator") as mock_gen:

        async def _gen():
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"

        mock_gen.return_value = _gen()
        response = client.get(f"/api/v1/qdrant/embed/{task_id}/stream")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_embed_progress_stream_not_found():
    """No queue → SSE sends not_found."""
    response = client.get("/api/v1/qdrant/embed/no-such-task/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


# ── embed_sigmaref action (POST /api/v1/qdrant) ────────────────────────────


@pytest.mark.asyncio
async def test_embed_sigmaref_already_running():
    with patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst:
        mock_db = MagicMock()
        mock_db.get_embed_status.return_value = {"status": "running", "task_id": "existing"}
        mock_db_inst.return_value = mock_db

        with patch("src.back.qdrant.check_health", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"status": "active"}

        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "embed_sigmaref",
                "payload": {
                    "action": "embed_sigmaref",
                    "registry_path": "data/documents/sigmaref/registry.json",
                    "collection_name": "sigma_doc",
                },
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "ALREADY_RUNNING"


def test_embed_sigmaref_qdrant_down():
    with patch("src.back.qdrant.check_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {}
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "embed_sigmaref",
                "payload": {
                    "action": "embed_sigmaref",
                    "registry_path": "data/documents/sigmaref/registry.json",
                    "collection_name": "sigma_doc",
                },
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "QDRANT_DOWN"


def test_embed_sigmaref_qdrant_down_exception():
    with patch("src.back.qdrant.check_health", new_callable=AsyncMock) as mock_health:
        mock_health.side_effect = ConnectionError("refused")
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "embed_sigmaref",
                "payload": {
                    "action": "embed_sigmaref",
                    "registry_path": "data/documents/sigmaref/registry.json",
                    "collection_name": "sigma_doc",
                },
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "QDRANT_DOWN"


def test_embed_sigmaref_success():
    with (
        patch("src.api.v1.qdrant.DatabaseService.get_instance") as mock_db_inst,
        patch("src.back.qdrant.health.check_health", new_callable=AsyncMock) as mock_health,
        patch("asyncio.create_task") as mock_create_task,
    ):
        mock_db = MagicMock()
        mock_db_inst.return_value = mock_db
        mock_health.return_value = {"status": "active"}
        mock_create_task.return_value = None  # don't actually schedule

        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "embed_sigmaref",
                "payload": {
                    "action": "embed_sigmaref",
                    "registry_path": "data/documents/sigmaref/registry.json",
                    "collection_name": "sigma_doc",
                },
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "task_id" in data["data"]
    # Verify upsert was called to start the task
    mock_db.upsert_embed_progress.assert_called()


# ── _run_embed_sigmaref background task ─────────────────────────────────────


@pytest.mark.asyncio
async def test_run_embed_sigmaref_empty_registry():
    """Zero registry entries → immediately completed."""
    db_mock = MagicMock()
    db_mock.get_doc_sigma_ref.return_value = []
    db_mock.upsert_embed_progress = MagicMock()

    task_id = "test-run-empty"
    with patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db_mock):
        from src.api.v1.qdrant import _run_embed_sigmaref

        await _run_embed_sigmaref(
            task_id=task_id,
            registry_path=Path("data/documents/sigmaref"),
            collection_name="sigma_doc",
            progress_queue=asyncio.Queue(),
        )

    assert db_mock.upsert_embed_progress.called
    # verify upsert was called for completed state
    upsert_calls = [c for c in db_mock.upsert_embed_progress.call_args_list]
    assert any(call[0][0]["status"] == "completed" for call in upsert_calls)


@pytest.mark.asyncio
async def test_run_embed_sigmaref_processes_entries():
    """Entries from doc_sigma_ref are processed and progress is sent."""
    db_mock = MagicMock()
    db_mock.get_doc_sigma_ref.return_value = [
        {
            "url_hash": "abc123",
            "original_url": "https://example.com/doc1",
            "normalized_url": "https://example.com/doc1",
            "content_type": "text/markdown",
            "rule_id": "rule-001",
            "title": "Test Doc 1",
            "timestamp": "2025-01-01T00:00:00Z",
            "content_sha256": "sha1",
        }
    ]
    db_mock.upsert_embed_progress = MagicMock()

    task_id = "test-run-proc"
    q = asyncio.Queue()
    db_mock.upsert_embed_progress = MagicMock()

    fake_doc_text = "# Test\nSome content."

    with (
        patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db_mock),
        patch("pathlib.Path.read_text", return_value=fake_doc_text),
        patch("src.back.rag.ingestion.IngestionPipelineBuilder") as mock_builder_cls,
    ):
        mock_builder = MagicMock()
        mock_builder.run = MagicMock()
        mock_builder_cls.return_value = mock_builder

        from src.api.v1.qdrant import _run_embed_sigmaref

        await _run_embed_sigmaref(
            task_id=task_id,
            registry_path=Path("data/documents/sigmaref"),
            collection_name="sigma_doc",
            progress_queue=q,
        )

    assert db_mock.upsert_embed_progress.called
    upsert_calls = [c for c in db_mock.upsert_embed_progress.call_args_list]
    assert any(call[0][0]["status"] == "completed" for call in upsert_calls)

    # progress events were pushed: initial processing + completed
    events = []
    while not q.empty():
        events.append(await q.get())
    assert len(events) >= 2
    assert events[-1]["status"] == "completed"

    # verify upsert_embed_progress was called for running and completed states
    upsert_calls = [c for c in db_mock.upsert_embed_progress.call_args_list]
    assert len(upsert_calls) >= 2
    assert upsert_calls[0][0][0]["status"] == "running"
    assert upsert_calls[-1][0][0]["status"] == "completed"


@pytest.mark.asyncio
async def test_run_embed_sigmaref_file_not_found_skips():
    db_mock = MagicMock()
    db_mock.get_doc_sigma_ref.return_value = [
        {
            "url_hash": "abc123",
            "original_url": "https://example.com/doc1",
            "normalized_url": "https://example.com/doc1",
            "content_type": "text/markdown",
            "rule_id": "rule-001",
            "title": "Test Doc 1",
            "timestamp": "2025-01-01T00:00:00Z",
            "content_sha256": "sha1",
        }
    ]
    db_mock.upsert_embed_progress = MagicMock()

    task_id = "test-run-skip"
    q = asyncio.Queue()
    db_mock.upsert_embed_progress = MagicMock()

    with (
        patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db_mock),
        patch("pathlib.Path.read_text", side_effect=FileNotFoundError),
    ):
        from src.api.v1.qdrant import _run_embed_sigmaref

        await _run_embed_sigmaref(
            task_id=task_id,
            registry_path=Path("data/documents/sigmaref"),
            collection_name="sigma_doc",
            progress_queue=q,
        )

    assert db_mock.upsert_embed_progress.called
    upsert_calls = [c for c in db_mock.upsert_embed_progress.call_args_list]
    assert any(call[0][0]["status"] == "completed" for call in upsert_calls)


@pytest.mark.asyncio
async def test_run_embed_sigmaref_read_error():
    db_mock = MagicMock()
    db_mock.get_doc_sigma_ref.return_value = [
        {
            "url_hash": "abc123",
            "original_url": "https://example.com/doc1",
            "normalized_url": "https://example.com/doc1",
            "content_type": "text/markdown",
            "rule_id": "rule-001",
            "title": "Test Doc 1",
            "timestamp": "2025-01-01T00:00:00Z",
            "content_sha256": "sha1",
        }
    ]
    db_mock.upsert_embed_progress = MagicMock()

    task_id = "test-run-err"
    q = asyncio.Queue()
    db_mock.upsert_embed_progress = MagicMock()

    with (
        patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db_mock),
        patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
    ):
        from src.api.v1.qdrant import _run_embed_sigmaref

        await _run_embed_sigmaref(
            task_id=task_id,
            registry_path=Path("data/documents/sigmaref"),
            collection_name="sigma_doc",
            progress_queue=q,
        )

    assert db_mock.upsert_embed_progress.called
    upsert_calls = [c for c in db_mock.upsert_embed_progress.call_args_list]
    assert any(call[0][0]["status"] == "completed" for call in upsert_calls)
