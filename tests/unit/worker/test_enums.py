"""Tests for worker enums."""

from src.worker.enums import WorkerName, WorkerStatus


class TestWorkerStatus:
    def test_idle_value(self) -> None:
        assert WorkerStatus.IDLE.value == "idle"

    def test_waiting_value(self) -> None:
        assert WorkerStatus.WAITING.value == "waiting"

    def test_running_value(self) -> None:
        assert WorkerStatus.RUNNING.value == "running"

    def test_error_value(self) -> None:
        assert WorkerStatus.ERROR.value == "error"


class TestWorkerName:
    def test_sigmaref_discovery(self) -> None:
        assert WorkerName.SIGMAREF_DISCOVERY.value == "sigmaref_discovery"

    def test_github_discovery(self) -> None:
        assert WorkerName.GITHUB_DISCOVERY.value == "github_discovery"

    def test_local_discovery(self) -> None:
        assert WorkerName.LOCAL_DISCOVERY.value == "local_discovery"

    def test_sigmaref_embeddings(self) -> None:
        assert WorkerName.SIGMAREF_EMBEDDINGS.value == "sigmaref_embeddings"

    def test_github_embeddings(self) -> None:
        assert WorkerName.GITHUB_EMBEDDINGS.value == "github_embeddings"

    def test_local_embeddings(self) -> None:
        assert WorkerName.LOCAL_EMBEDDINGS.value == "local_embeddings"

    def test_model_sync(self) -> None:
        assert WorkerName.MODEL_SYNC.value == "model_sync"

    def test_local_repo_sync(self) -> None:
        assert WorkerName.LOCAL_REPO_SYNC.value == "local_repo_sync"

    def test_all_members_present(self) -> None:
        names = [m.value for m in WorkerName]
        assert "sigmaref_discovery" in names
        assert "github_discovery" in names
        assert "local_discovery" in names
        assert "sigmaref_embeddings" in names
        assert "github_embeddings" in names
        assert "local_embeddings" in names
        assert "model_sync" in names
        assert "local_repo_sync" in names
