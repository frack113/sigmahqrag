"""Tests for embed_sigmaref SSE endpoints and background task."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.qdrant import router, _embed_tasks, _embed_progress_queues

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_embed_state():
    yield
    _embed_tasks.clear()
    _embed_progress_queues.clear()


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
    from src.api.v1.qdrant import _embed_progress_generator

    task_id = "test-gen-001"
    q = asyncio.Queue()
    _embed_progress_queues[task_id] = q
    await q.put({"status": "processing", "processed": 1, "total": 5})
    await q.put({"status": "completed", "processed": 5, "total": 5})

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
    q = asyncio.Queue()
    _embed_progress_queues[task_id] = q
    await q.put({"status": "failed", "error": "boom"})

    events = [e async for e in _embed_progress_generator(task_id)]
    assert len(events) == 1
    data = json.loads(events[0].removeprefix("data: ").strip())
    assert data["status"] == "failed"


@pytest.mark.asyncio
async def test_generator_timeout_on_empty_queue():
    from src.api.v1.qdrant import _embed_progress_generator

    task_id = "test-gen-timeout"
    q = asyncio.Queue()
    _embed_progress_queues[task_id] = q

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
    _embed_tasks[task_id] = {"id": task_id, "status": "running", "total": 5}

    response = client.get(f"/api/v1/qdrant/embed/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["task_id"] == task_id


# ── embed_progress_stream endpoint (GET /embed/{task_id}/stream) ────────────


def test_embed_progress_stream_sse():
    task_id = "test-stream-001"
    q = asyncio.Queue()
    _embed_progress_queues[task_id] = q

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


def test_embed_sigmaref_already_running():
    _embed_tasks["existing"] = {"id": "existing", "status": "running"}

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
        patch("src.back.qdrant.health.check_health", new_callable=AsyncMock) as mock_health,
        patch("asyncio.create_task") as mock_create_task,
    ):
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
    assert data["message"] == "SigmaRef embedding started"
    # task stored in _embed_tasks
    assert data["data"]["task_id"] in _embed_tasks


# ── _run_embed_sigmaref background task ─────────────────────────────────────


@pytest.mark.asyncio
async def test_run_embed_sigmaref_empty_registry():
    """Zero registry entries → immediately completed."""
    db_mock = MagicMock()
    db_mock.get_doc_sigma_ref.return_value = []
    db_mock.upsert_embed_progress = MagicMock()

    task_id = "test-run-empty"
    q = asyncio.Queue()
    _embed_tasks[task_id] = {"id": task_id, "status": "pending"}
    _embed_progress_queues[task_id] = q

    with patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db_mock):
        from src.api.v1.qdrant import _run_embed_sigmaref

        await _run_embed_sigmaref(
            task_id=task_id,
            registry_path=Path("data/documents/sigmaref"),
            collection_name="sigma_doc",
            progress_queue=q,
        )

    assert _embed_tasks[task_id]["status"] == "completed"

    events = []
    while not q.empty():
        events.append(await q.get())
    assert len(events) == 1
    assert events[0]["status"] == "completed"
    assert "No files found" in events[0]["message"]


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
    _embed_tasks[task_id] = {"id": task_id, "status": "pending"}
    _embed_progress_queues[task_id] = q

    fake_doc_text = "# Test\nSome content."

    with (
        patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db_mock),
        patch("pathlib.Path.read_text", return_value=fake_doc_text) as mock_read,
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

    assert _embed_tasks[task_id]["status"] == "completed"
    assert _embed_tasks[task_id]["processed"] == 1
    assert _embed_tasks[task_id]["total"] == 1
    mock_read.assert_called_once()
    mock_builder.run.assert_called_once()

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
    _embed_tasks[task_id] = {"id": task_id, "status": "pending"}
    _embed_progress_queues[task_id] = q

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

    assert _embed_tasks[task_id]["status"] == "completed"
    assert "skipped" in _embed_tasks[task_id]
    assert len(_embed_tasks[task_id]["skipped"]) == 1

    events = []
    while not q.empty():
        events.append(await q.get())
    assert events[-1]["status"] == "completed"


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
    _embed_tasks[task_id] = {"id": task_id, "status": "pending"}
    _embed_progress_queues[task_id] = q

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

    assert _embed_tasks[task_id]["status"] == "completed"
    assert "errors" in _embed_tasks[task_id]
    assert len(_embed_tasks[task_id]["errors"]) == 1

    events = []
    while not q.empty():
        events.append(await q.get())
    assert events[-1]["status"] == "completed"
