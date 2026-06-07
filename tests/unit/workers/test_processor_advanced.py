"""Advanced tests for TaskDispatcher — coverage for remaining methods."""

from __future__ import annotations

from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from src.workers.processor import TaskDispatcher
from src.workers.enums import WorkerName, WorkerStatus


class TestGetAllWorkerStates:
    def test_returns_state_list(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY)
            states = d.get_all_worker_states()
            assert len(states) == 1
            assert states[0]["worker_type"] == WorkerName.SIGMAREF_DISCOVERY.value
            assert states[0]["status"] == WorkerStatus.WAITING.value

    def test_returns_empty_when_none(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            assert d.get_all_worker_states() == []


class TestUpdateWorkerState:
    def test_updates_existing_state(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY)
            d.update_worker_state(WorkerName.SIGMAREF_DISCOVERY, progress_percent=50)
            state = d._worker_states[WorkerName.SIGMAREF_DISCOVERY]
            assert state["progress_percent"] == 50

    def test_creates_state_if_missing(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.update_worker_state(WorkerName.GITHUB_DISCOVERY, progress_percent=10)
            state = d._worker_states[WorkerName.GITHUB_DISCOVERY]
            assert state["status"] == WorkerStatus.IDLE
            assert state["progress_percent"] == 10
            assert state["current_task_id"] == ""


class TestGetWorkerProgress:
    def test_returns_progress(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY)
            progress = d.get_worker_progress(WorkerName.SIGMAREF_DISCOVERY.value)
            assert progress is not None
            assert progress["status"] == WorkerStatus.WAITING.value
            assert "current_task_id" not in progress

    def test_returns_none_for_unknown(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            assert d.get_worker_progress("nonexistent") is None


class TestIsWorkerBusy:
    def test_returns_true_when_not_idle(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY)
            assert d.is_worker_busy(WorkerName.SIGMAREF_DISCOVERY) is True

    def test_returns_false_when_idle(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            assert d.is_worker_busy(WorkerName.SIGMAREF_DISCOVERY) is False

    def test_returns_false_for_unknown(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            assert d.is_worker_busy(WorkerName.MODEL_SYNC) is False


class TestGetProgressWorker:
    def test_returns_progress_percent(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY)
            assert d.get_progress_worker(WorkerName.SIGMAREF_DISCOVERY) == 0

    def test_returns_zero_for_unknown(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            assert d.get_progress_worker(WorkerName.MODEL_SYNC) == 0


class TestAskForWorkerReject:
    def test_rejects_when_running(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY)
            d._worker_states[WorkerName.SIGMAREF_DISCOVERY]["status"] = WorkerStatus.RUNNING
            assert d.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY) is None


class TestRunWorker:
    def _setup_state(self, d):
        from src.workers.enums import WorkerStatus

        d._worker_states[WorkerName.SIGMAREF_DISCOVERY] = {
            "status": WorkerStatus.IDLE,
            "current_task_id": "",
            "error": "",
            "progress_percent": 0,
            "current_file": "",
        }

    def test_completes_successfully(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._db = mock_db
            self._setup_state(d)
            mock_worker = MagicMock()
            d._run_worker(WorkerName.SIGMAREF_DISCOVERY, mock_worker, {"task_id": "test-1"})
            mock_worker.process.assert_called_once()
            assert d._worker_states[WorkerName.SIGMAREF_DISCOVERY]["status"] == WorkerStatus.IDLE

    def test_handles_exception(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._db = mock_db
            self._setup_state(d)
            mock_worker = MagicMock()
            mock_worker.process.side_effect = RuntimeError("fail")
            with (
                patch("src.workers.processor.logger") as mock_log,
                pytest.raises(RuntimeError),
            ):
                d._run_worker(WorkerName.SIGMAREF_DISCOVERY, mock_worker, {"task_id": "test-2"})
            mock_log.error.assert_called()
            state = d._worker_states[WorkerName.SIGMAREF_DISCOVERY]
            assert state["error"] == "fail"

    def test_re_raises_exception(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._db = mock_db
            self._setup_state(d)
            mock_worker = MagicMock()
            mock_worker.process.side_effect = RuntimeError("fail")
            with pytest.raises(RuntimeError):
                d._run_worker(WorkerName.SIGMAREF_DISCOVERY, mock_worker, {"task_id": "test-3"})


class TestRunLoop:
    def test_handles_missing_task(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._running = True
            d._pending_tasks = {}
            d._workers = {}
            d._executor = MagicMock()
            d._worker_states[WorkerName.SIGMAREF_DISCOVERY] = {
                "status": WorkerStatus.WAITING,
                "current_task_id": "orphan",
                "error": "",
                "progress_percent": 0,
                "current_file": "",
            }
            d._stop_event.set()
            d._run_loop()
            state = d._worker_states[WorkerName.SIGMAREF_DISCOVERY]
            assert state["status"] == WorkerStatus.IDLE

    def test_launches_worker_from_waiting(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._running = True
            mock_worker = MagicMock()
            d._workers = {WorkerName.SIGMAREF_DISCOVERY: mock_worker}
            d._executor = MagicMock()
            d._pending_tasks[WorkerName.SIGMAREF_DISCOVERY] = {"task_id": "run-1"}
            d._worker_states[WorkerName.SIGMAREF_DISCOVERY] = {
                "status": WorkerStatus.WAITING,
                "current_task_id": "run-1",
                "error": "",
                "progress_percent": 0,
                "current_file": "",
            }
            d._stop_event.set()
            d._run_loop()
            d._executor.submit.assert_called_once()

    def test_handles_submit_failure(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._running = True
            mock_worker = MagicMock()
            d._workers = {WorkerName.SIGMAREF_DISCOVERY: mock_worker}
            mock_executor = MagicMock()
            mock_executor.submit.side_effect = RuntimeError("submit failed")
            d._executor = mock_executor
            d._pending_tasks[WorkerName.SIGMAREF_DISCOVERY] = {"task_id": "submit-fail"}
            d._worker_states[WorkerName.SIGMAREF_DISCOVERY] = {
                "status": WorkerStatus.WAITING,
                "current_task_id": "submit-fail",
                "error": "",
                "progress_percent": 0,
                "current_file": "",
            }
            d._stop_event.set()
            d._run_loop()
            state = d._worker_states[WorkerName.SIGMAREF_DISCOVERY]
            assert state["status"] == WorkerStatus.IDLE
            assert "submit failed" in state["error"]

    def test_handles_missing_worker_type(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            d._running = True
            d._workers = {}
            d._executor = MagicMock()
            d._pending_tasks[WorkerName.SIGMAREF_DISCOVERY] = {"task_id": "miss-1"}
            d._worker_states[WorkerName.SIGMAREF_DISCOVERY] = {
                "status": WorkerStatus.WAITING,
                "current_task_id": "miss-1",
                "error": "",
                "progress_percent": 0,
                "current_file": "",
            }
            d._stop_event.set()
            d._run_loop()
            state = d._worker_states[WorkerName.SIGMAREF_DISCOVERY]
            assert state["status"] == WorkerStatus.IDLE
            assert "No worker registered" in state["error"]


class TestOnTaskDone:
    def test_logs_exception(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            future: Future = Future()
            future.set_exception(RuntimeError("task failed"))
            with patch("src.workers.processor.logger") as mock_log:
                d._on_task_done(future)
            mock_log.error.assert_called()

    def test_no_exception_no_log(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            future: Future = Future()
            future.set_result(None)
            with patch("src.workers.processor.logger") as mock_log:
                d._on_task_done(future)
            mock_log.error.assert_not_called()

    def test_handles_future_exception_retrieval_error(self, mock_db: MagicMock) -> None:
        with patch("src.workers.processor.DatabaseService.get_instance", return_value=mock_db):
            d = TaskDispatcher()
            future: Future = Future()
            future.set_result(None)
            with patch.object(future, "exception", side_effect=RuntimeError("retrieval error")):
                with patch("src.workers.processor.logger") as mock_log:
                    d._on_task_done(future)
                mock_log.error.assert_called()
