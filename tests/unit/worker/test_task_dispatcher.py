"""Tests for TaskDispatcher."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from src.worker.processor import TaskDispatcher


class TestTaskDispatcherInit:
    def test_default_poll_interval(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            assert dispatcher.poll_interval == 5

    def test_custom_poll_interval(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher(poll_interval=10)
            assert dispatcher.poll_interval == 10

    def test_registers_six_workers(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            # Workers are created in the thread, not in __init__
            assert dispatcher._running is False
            assert dispatcher._task_queue is not None


class TestTaskDispatcherQueue:
    @pytest.mark.asyncio
    async def test_queue_task(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            await dispatcher.queue_task("sigmaref_discovery", {"task_id": "test-1"})

        item = dispatcher._task_queue.get_nowait()
        assert item == ("sigmaref_discovery", {"task_id": "test-1"})


class TestTaskDispatcherThread:
    def test_start_creates_thread(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            dispatcher.start()
            time.sleep(0.5)
            assert dispatcher._thread is not None
            assert dispatcher._thread.is_alive()
            dispatcher.stop()

    def test_stop_joins_thread(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            dispatcher.start()
            time.sleep(0.5)
            dispatcher.stop()
            assert not dispatcher._thread.is_alive()

    def test_stop_when_not_started(self, mock_db: MagicMock) -> None:
        with patch("src.worker.processor.DatabaseService.get_instance", return_value=mock_db):
            dispatcher = TaskDispatcher()
            dispatcher.stop()  # Should not raise
