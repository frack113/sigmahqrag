"""Tests for TaskDispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.back.worker.processor import TaskDispatcher


class TestTaskDispatcherInit:
    def test_default_poll_interval(self, mock_db: MagicMock) -> None:
        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            assert dispatcher.poll_interval == 5

    def test_custom_poll_interval(self, mock_db: MagicMock) -> None:
        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher(poll_interval=10)
            assert dispatcher.poll_interval == 10

    def test_registers_six_workers(self, mock_db: MagicMock) -> None:
        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            expected = {
                "sigmaref_discovery",
                "github_discovery",
                "local_discovery",
                "sigmaref_embeddings",
                "github_embeddings",
                "local_embeddings",
            }
            assert set(dispatcher._workers.keys()) == expected

    def test_stop_sets_running_false(self, mock_db: MagicMock) -> None:
        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            dispatcher._running = True
            dispatcher.stop()
            assert dispatcher._running is False


class TestTaskDispatcherDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_skips_already_claimed(
        self, mock_db: MagicMock, sample_task: dict
    ) -> None:
        mock_db.claim_task.return_value = False

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            await dispatcher._dispatch(sample_task)

        mock_db.claim_task.assert_called_once_with("test-task-001")
        mock_db.upsert_worker_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_unknown_worker_type(
        self, mock_db: MagicMock, sample_task: dict
    ) -> None:
        mock_db.claim_task.return_value = True
        sample_task["task_type"] = "unknown_type"

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            await dispatcher._dispatch(sample_task)

        mock_db.upsert_embed_progress.assert_any_call(
            task_id="test-task-001",
            status="failed",
            errors="No worker registered for task type: unknown_type",
            collection_name="test-org/test-repo",
        )
        mock_db.upsert_worker_state.assert_any_call(
            worker_type="unknown_type",
            status="idle",
            current_task_id="",
            error="No worker registered for task type: unknown_type",
        )

    @pytest.mark.asyncio
    async def test_dispatch_sets_worker_state_running(
        self, mock_db: MagicMock, sample_task: dict
    ) -> None:
        mock_db.claim_task.return_value = True

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            await dispatcher._dispatch(sample_task)

        mock_db.upsert_worker_state.assert_any_call(
            worker_type="test",
            status="running",
            current_task_id="test-task-001",
        )

    @pytest.mark.asyncio
    async def test_dispatch_resets_worker_state_after_completion(
        self, mock_db: MagicMock, sample_task: dict
    ) -> None:
        mock_db.claim_task.return_value = True

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            await dispatcher._dispatch(sample_task)

        calls = [c for c in mock_db.upsert_worker_state.call_args_list]
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "idle"
        assert final_call.kwargs["current_task_id"] == ""


class TestTaskDispatcherRun:
    @pytest.mark.asyncio
    async def test_run_resets_stale_on_start(self, mock_db: MagicMock) -> None:
        mock_db.get_active_embed_tasks.return_value = []

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher(poll_interval=1)

            async def stop_after_one_iteration(*_args, **_kwargs):
                dispatcher.stop()

            with patch("asyncio.sleep", side_effect=stop_after_one_iteration):
                await dispatcher.run()

        mock_db.reset_stale_embed_tasks.assert_called_once()
        mock_db.reset_stale_workers.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_dispatches_pending_tasks(self, mock_db: MagicMock) -> None:
        pending_task = {
            "task_id": "task-1",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
            "status": "pending",
        }
        mock_db.get_active_embed_tasks.side_effect = [[pending_task], []]
        mock_db.claim_task.return_value = True

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher(poll_interval=1)

            async def stop_after_dispatch(*_args, **_kwargs):
                dispatcher.stop()

            with patch("asyncio.sleep", side_effect=stop_after_dispatch):
                await dispatcher.run()

        mock_db.claim_task.assert_called_with("task-1")

    @pytest.mark.asyncio
    async def test_run_skips_running_tasks(self, mock_db: MagicMock) -> None:
        running_task = {
            "task_id": "task-1",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "status": "running",
        }
        mock_db.get_active_embed_tasks.side_effect = [[running_task], []]

        with patch("src.back.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher(poll_interval=1)

            async def stop_after_iteration(*_args, **_kwargs):
                dispatcher.stop()

            with patch("asyncio.sleep", side_effect=stop_after_iteration):
                await dispatcher.run()

        mock_db.claim_task.assert_not_called()
