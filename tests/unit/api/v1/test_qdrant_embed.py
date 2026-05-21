"""Tests for embed worker progress endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.qdrant import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_app_state():
    yield
    if hasattr(app.state, "dispatcher"):
        del app.state.dispatcher


# ── _embed_progress_generator ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generator_not_found():
    """Unknown worker_type yields not_found immediately."""
    from src.api.v1.qdrant import _embed_progress_generator

    mock_dispatcher = MagicMock()
    mock_dispatcher.get_worker_progress.return_value = None

    events = [e async for e in _embed_progress_generator("no-such-worker", mock_dispatcher)]
    assert len(events) == 1
    data = json.loads(events[0].removeprefix("data: ").strip())
    assert data["status"] == "not_found"


@pytest.mark.asyncio
async def test_generator_yields_events_breaks_on_completed():
    from src.api.v1.qdrant import _embed_progress_generator

    worker_type = "sigmaref_embeddings"
    mock_dispatcher = MagicMock()
    mock_dispatcher.get_worker_progress.side_effect = [
        {"status": "running", "progress_percent": 20.0},
        {"status": "completed", "progress_percent": 100.0},
    ]

    events = [e async for e in _embed_progress_generator(worker_type, mock_dispatcher)]
    assert len(events) == 2
    d1 = json.loads(events[0].removeprefix("data: ").strip())
    assert d1["status"] == "running"
    d2 = json.loads(events[1].removeprefix("data: ").strip())
    assert d2["status"] == "completed"


@pytest.mark.asyncio
async def test_generator_breaks_on_failed():
    from src.api.v1.qdrant import _embed_progress_generator

    worker_type = "github_embeddings"
    mock_dispatcher = MagicMock()
    mock_dispatcher.get_worker_progress.return_value = {"status": "failed", "error": "boom"}

    events = [e async for e in _embed_progress_generator(worker_type, mock_dispatcher)]
    assert len(events) == 1
    data = json.loads(events[0].removeprefix("data: ").strip())
    assert data["status"] == "failed"


# ── embed_progress endpoint (GET /embed/{worker_type}) ──────────────────────


def test_embed_progress_not_found():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = None

    response = client.get("/api/v1/qdrant/embed/no-such-worker")
    assert response.status_code == 404
    assert response.json()["status"] == "not_found"


def test_embed_progress_found():
    worker_type = "sigmaref_embeddings"
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = {
        "status": "running",
        "progress_percent": 50.0,
    }

    response = client.get(f"/api/v1/qdrant/embed/{worker_type}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["worker_type"] == worker_type


# ── embed_progress_stream endpoint (GET /embed/{worker_type}/stream) ────────


@pytest.mark.asyncio
async def test_embed_progress_stream_sse():
    worker_type = "sigmaref_embeddings"
    app.state.dispatcher = MagicMock()

    with patch("src.api.v1.qdrant._embed_progress_generator") as mock_gen:

        async def _gen():
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"

        mock_gen.return_value = _gen()
        response = client.get(f"/api/v1/qdrant/embed/{worker_type}/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


def test_embed_progress_stream_not_found():
    app.state.dispatcher = MagicMock()

    with patch("src.api.v1.qdrant._embed_progress_generator") as mock_gen:

        async def _gen():
            yield f"data: {json.dumps({'status': 'not_found'})}\n\n"

        mock_gen.return_value = _gen()
        response = client.get("/api/v1/qdrant/embed/no-such-worker/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


# ── worker embed-status endpoint (GET /embed-status/{worker_type}) ──────────


def test_worker_embed_status_not_found():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = None

    response = client.get("/api/v1/qdrant/embed-status/no-such-worker")
    assert response.status_code == 404


def test_worker_embed_status_found():
    worker_type = "github_embeddings"
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = {
        "status": "running",
        "progress_percent": 75.0,
        "current_file": "rule.yml",
        "error": None,
    }

    response = client.get(f"/api/v1/qdrant/embed-status/{worker_type}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["progress_percent"] == 75.0


# ── embed_sigmaref action (POST /api/v1/qdrant) ────────────────────────────


def test_embed_sigmaref_already_running():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.ask_for_worker.return_value = False

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
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.ask_for_worker.return_value = True

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
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.ask_for_worker.return_value = True

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
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.ask_for_worker.return_value = "generated-task-1"

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
    assert data["status"] == "success"
    assert data["data"]["task_id"] == "generated-task-1"
