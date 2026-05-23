"""Tests for TaskDispatcher API v1 endpoints."""

import importlib
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

router = importlib.import_module("src.api.v1.dispatcher").router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ── GET /api/v1/dispatcher/progress/{worker_type} ────────────────────────────


def test_progress_unknown_worker():
    app.state.dispatcher = MagicMock()
    response = client.get("/api/v1/dispatcher/progress/no_such_worker")
    assert response.status_code == 400


def test_progress_ok():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_progress_worker.return_value = 42

    response = client.get("/api/v1/dispatcher/progress/sigmaref_embeddings")
    assert response.status_code == 200
    data = response.json()
    assert data["progress_percent"] == 42
    assert data["worker_type"] == "sigmaref_embeddings"


# ── POST /api/v1/dispatcher/ask ──────────────────────────────────────────────


def test_ask_unknown_worker_type():
    app.state.dispatcher = MagicMock()
    response = client.post(
        "/api/v1/dispatcher/ask",
        json={"worker_type": "no_such_worker", "task_params": {}},
    )
    assert response.status_code == 400


def test_ask_worker_busy():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.ask_for_worker.return_value = None

    response = client.post(
        "/api/v1/dispatcher/ask",
        json={"worker_type": "sigmaref_embeddings", "task_params": {"collection_name": "test"}},
    )
    assert response.status_code == 409


def test_ask_worker_ok():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.ask_for_worker.return_value = "task-123"

    response = client.post(
        "/api/v1/dispatcher/ask",
        json={"worker_type": "github_embeddings", "task_params": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-123"
    assert data["worker_type"] == "github_embeddings"


# ── GET /api/v1/dispatcher/status/{worker_type} ──────────────────────────────


def test_status_not_found():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = None

    response = client.get("/api/v1/dispatcher/status/no_such_worker")
    assert response.status_code == 404


def test_status_ok():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = {
        "status": "running",
        "progress_percent": 50.0,
    }

    response = client.get("/api/v1/dispatcher/status/sigmaref_embeddings")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["progress_percent"] == 50.0


# ── GET /api/v1/dispatcher/status/{worker_type}/stream (SSE) ─────────────────


def test_status_stream_not_found():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = None

    response = client.get("/api/v1/dispatcher/status/no-such-worker/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_status_stream_ok():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_worker_progress.return_value = {
        "status": "idle",
        "progress_percent": 100.0,
    }

    response = client.get("/api/v1/dispatcher/status/sigmaref_embeddings/stream")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


# ── GET /api/v1/dispatcher/status ────────────────────────────────────────────


def test_all_worker_status():
    app.state.dispatcher = MagicMock()
    app.state.dispatcher.get_all_worker_states.return_value = [
        {"worker_type": "sigmaref_embeddings", "status": "idle"},
        {"worker_type": "model_sync", "status": "running"},
    ]

    response = client.get("/api/v1/dispatcher/status")
    assert response.status_code == 200
    data = response.json()
    assert len(data["workers"]) == 2
