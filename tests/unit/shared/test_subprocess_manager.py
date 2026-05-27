"""Tests for subprocess manager."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.subprocess_manager import ServiceProcess, SubprocessManager


class TestServiceProcess:
    def test_default_values(self) -> None:
        sp = ServiceProcess(name="test")
        assert sp.name == "test"
        assert sp.process is None
        assert sp.pid is None
        assert sp.log_file is None
        assert sp.pid_file is None
        assert sp.log_handle is None
        assert sp.is_running is False


class TestSubprocessManagerInit:
    def test_initializes_empty(self, tmp_path: Path) -> None:
        logs = tmp_path / "logs"
        pids = tmp_path / "pids"
        pids.mkdir(parents=True)
        mgr = SubprocessManager(logs_dir=logs, pid_dir=pids)
        assert mgr.logs_dir == logs
        assert mgr.pid_dir == pids
        assert mgr._processes == {}

    def test_syncs_from_pid_files(self, tmp_path: Path) -> None:
        logs = tmp_path / "logs"
        pids = tmp_path / "pids"
        pids.mkdir(parents=True)
        (pids / "myservice.pid").write_text("99999")

        with patch.object(SubprocessManager, "_is_process_running", return_value=True):
            mgr = SubprocessManager(logs_dir=logs, pid_dir=pids)
            assert "myservice" in mgr._processes
            assert mgr._processes["myservice"].pid == 99999
            assert mgr._processes["myservice"].is_running is True

    def test_removes_stale_pid_files(self, tmp_path: Path) -> None:
        logs = tmp_path / "logs"
        pids = tmp_path / "pids"
        pids.mkdir(parents=True)
        pid_file = pids / "stale.pid"
        pid_file.write_text("99999")

        with patch.object(SubprocessManager, "_is_process_running", return_value=False):
            mgr = SubprocessManager(logs_dir=logs, pid_dir=pids)
            assert "stale" not in mgr._processes
            assert not pid_file.exists()

    def test_handles_invalid_pid_file(self, tmp_path: Path) -> None:
        logs = tmp_path / "logs"
        pids = tmp_path / "pids"
        pids.mkdir(parents=True)
        (pids / "bad.pid").write_text("not-a-number")
        mgr = SubprocessManager(logs_dir=logs, pid_dir=pids)
        assert "bad" not in mgr._processes


class TestIsProcessRunning:
    def test_running_process(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        with patch("os.kill", return_value=None):
            assert mgr._is_process_running(12345) is True

    def test_not_running(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        with patch("os.kill", side_effect=ProcessLookupError):
            assert mgr._is_process_running(99999) is False

    def test_oserror(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        with patch("os.kill", side_effect=OSError):
            assert mgr._is_process_running(99999) is False


class TestIsHealthy:
    def test_unknown_service(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        assert mgr.is_healthy("nonexistent") is False

    def test_not_running(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc", is_running=False)
        assert mgr.is_healthy("svc") is False

    def test_no_pid(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc", is_running=True, pid=None)
        assert mgr.is_healthy("svc") is False

    def test_process_not_running(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc", is_running=True, pid=99999)
        with patch.object(mgr, "_is_process_running", return_value=False):
            assert mgr.is_healthy("svc") is False

    def test_healthy(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc", is_running=True, pid=12345)
        with patch.object(mgr, "_is_process_running", return_value=True):
            assert mgr.is_healthy("svc") is True


class TestGetLogs:
    def test_no_log_file(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc")
        result = mgr.get_logs("svc")
        assert "No log file found" in result

    def test_log_file_does_not_exist(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc", log_file=Path("/nonexistent/svc.log"))
        result = mgr.get_logs("svc")
        assert "does not exist" in result

    def test_reads_log_content(self, tmp_path: Path) -> None:
        log_file = tmp_path / "svc.log"
        log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(name="svc", log_file=log_file)
        result = mgr.get_logs("svc")
        assert result == "line1\nline2\nline3\n"

    def test_unknown_service(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        result = mgr.get_logs("unknown")
        assert "No log file found" in result


class TestStopAll:
    @pytest.mark.asyncio
    async def test_stops_all_services(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc1"] = ServiceProcess(name="svc1", is_running=True)
        mgr._processes["svc2"] = ServiceProcess(name="svc2", is_running=True)
        mgr.stop_service = AsyncMock(return_value={"success": True})

        results = await mgr.stop_all()
        assert "svc1" in results
        assert "svc2" in results

    @pytest.mark.asyncio
    async def test_no_running_services(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        results = await mgr.stop_all()
        assert results == {}


class TestShutdown:
    def test_shuts_down_all(self) -> None:
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_log_handle = MagicMock()
        mock_pid_file = MagicMock()

        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr._processes["svc"] = ServiceProcess(
            name="svc",
            process=mock_process,
            log_handle=mock_log_handle,
            pid_file=mock_pid_file,
        )

        with patch("src.shared.subprocess_manager.signal"):
            mgr.shutdown()
            mock_process.send_signal.assert_called_once()
            mock_log_handle.close.assert_called_once()
            mock_pid_file.unlink.assert_called_once_with(missing_ok=True)
            assert mgr._processes == {}

    def test_shutdown_empty(self) -> None:
        mgr = SubprocessManager(logs_dir=Path("/tmp/logs"), pid_dir=Path("/tmp/pids"))
        mgr.shutdown()
        assert mgr._processes == {}
