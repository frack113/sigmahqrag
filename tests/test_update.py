"""Tests for update management."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.admin.backup_manager import (
    BackupManager,
    BackupMetadata,
    create_backup_manager,
)
from src.admin.update_manager import (
    UpdateService,
    create_update_service,
)
from src.exceptions import BackupError, UpdateError


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_dir = Path(tmpdir) / "bin"
        backup_dir = Path(tmpdir) / "backups"
        bin_dir.mkdir(parents=True)
        backup_dir.mkdir(parents=True)
        yield bin_dir, backup_dir


@pytest.fixture
def backup_manager(temp_dirs):
    """Create a backup manager with temp directories."""
    bin_dir, backup_dir = temp_dirs
    with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
        with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
            manager = BackupManager(backup_dir=backup_dir, max_backups=3)
            yield manager


@pytest.fixture
def mock_health_checker():
    """Create a mock health checker."""
    mock = MagicMock()
    health_running = MagicMock()
    health_running.status = MagicMock()
    health_running.status.name = "RUNNING"
    mock.check_llama = AsyncMock(return_value=health_running)
    mock.check_qdrant = AsyncMock(return_value=health_running)
    return mock


class TestBackupManager:
    """Tests for BackupManager."""

    @pytest.mark.asyncio
    async def test_create_backup(self, backup_manager, temp_dirs):
        """Test backup creation."""
        bin_dir, backup_dir = temp_dirs

        binary_path = bin_dir / "llama-server"
        binary_path.write_bytes(b"fake binary content")

        version_file = backup_dir / "versions.json"
        version_file.write_text(json.dumps({"llama.cpp": {"version": "v1.0.0"}}))

        metadata = await backup_manager.create_backup("llama.cpp", "v1.0.0")

        assert metadata.service == "llama.cpp"
        assert metadata.version == "v1.0.0"
        assert metadata.backup_id.startswith("backup-llama-cpp-v1.0.0-")

    @pytest.mark.asyncio
    async def test_create_backup_binary_not_found(self, backup_manager):
        """Test backup creation when binary doesn't exist."""
        with pytest.raises(BackupError, match="Binary not found"):
            await backup_manager.create_backup("llama.cpp", "v1.0.0")

    @pytest.mark.asyncio
    async def test_list_backups(self, backup_manager, temp_dirs):
        """Test listing backups."""
        bin_dir, _ = temp_dirs

        binary_path = bin_dir / "llama-server"
        binary_path.write_bytes(b"fake binary content")

        metadata1 = await backup_manager.create_backup("llama.cpp", "v1.0.0")
        metadata2 = await backup_manager.create_backup("llama.cpp", "v1.1.0")

        backups = await backup_manager.list_backups("llama.cpp")

        assert len(backups) == 2
        assert backups[0].backup_id == metadata2.backup_id
        assert backups[1].backup_id == metadata1.backup_id

    @pytest.mark.asyncio
    async def test_restore_backup(self, backup_manager, temp_dirs):
        """Test restoring from backup."""
        bin_dir, backup_dir = temp_dirs

        binary_path = bin_dir / "llama-server"
        binary_path.write_bytes(b"original content")

        await backup_manager.create_backup("llama.cpp", "v1.0.0")

        binary_path.write_bytes(b"updated content")

        backups = await backup_manager.list_backups("llama.cpp")
        metadata, restored = await backup_manager.restore_backup(
            "llama.cpp", backups[0].backup_id
        )

        assert binary_path.read_bytes() == b"original content"
        assert metadata.version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self, temp_dirs):
        """Test cleanup of old backups."""
        bin_dir, backup_dir = temp_dirs

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
                manager = BackupManager(backup_dir=backup_dir, max_backups=2)

                binary_path = bin_dir / "llama-server"
                binary_path.write_bytes(b"test content")

                await manager.create_backup("llama.cpp", "v1.0.0")
                await manager.create_backup("llama.cpp", "v1.1.0")
                await manager.create_backup("llama.cpp", "v1.2.0")

                backups = await manager.list_backups("llama.cpp")

                assert len(backups) == 2

    @pytest.mark.asyncio
    async def test_get_current_version(self, backup_manager, temp_dirs):
        """Test getting current version."""
        _, backup_dir = temp_dirs

        version_file = backup_dir / "versions.json"
        version_file.write_text(json.dumps({"llama.cpp": {"version": "v1.0.0"}}))

        version = backup_manager.get_current_version("llama.cpp")

        assert version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_update_version_metadata(self, backup_manager, temp_dirs):
        """Test updating version metadata."""
        _, backup_dir = temp_dirs

        await backup_manager.update_version_metadata("llama.cpp", "v1.2.0")

        version_file = backup_dir / "versions.json"
        data = json.loads(version_file.read_text())

        assert data["llama.cpp"]["version"] == "v1.2.0"


class TestUpdateService:
    """Tests for UpdateService."""

    @pytest.mark.asyncio
    async def test_apply_update_success(
        self, backup_manager, mock_health_checker, temp_dirs
    ):
        """Test successful update application."""
        bin_dir, backup_dir = temp_dirs

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
                binary_path_new = bin_dir / "llama-server-new"
                binary_path_new.write_bytes(b"new binary content")

                binary_path = bin_dir / "llama-server"
                binary_path.write_bytes(b"old binary content")

                version_file = backup_dir / "versions.json"
                version_file.write_text(
                    json.dumps({"llama.cpp": {"version": "v1.0.0"}})
                )

                service = UpdateService(
                    backup_manager=backup_manager,
                    health_checker=mock_health_checker,
                )

                result = await service.apply_update(
                    service="llama.cpp",
                    version="v1.1.0",
                    binary_path=binary_path_new,
                )

                assert result["status"] == "success"
                assert result["version"] == "v1.1.0"

    @pytest.mark.asyncio
    async def test_apply_update_health_check_fail(
        self, backup_manager, temp_dirs
    ):
        """Test update with health check failure triggers rollback."""
        bin_dir, backup_dir = temp_dirs

        mock_failing_checker = AsyncMock()
        mock_failing_checker.check_llama = AsyncMock(
            return_value=MagicMock(status=MagicMock(name="STOPPED"))
        )

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
                binary_path = bin_dir / "llama-server-new"
                binary_path.write_bytes(b"new binary content")

                version_file = backup_dir / "versions.json"
                version_file.write_text(
                    json.dumps({"llama.cpp": {"version": "v1.0.0"}})
                )

                service = UpdateService(
                    backup_manager=backup_manager,
                    health_checker=mock_failing_checker,
                )

                result = await service.apply_update(
                    service="llama.cpp",
                    version="v1.1.0",
                    binary_path=binary_path,
                )

                assert result["status"] == "failed"
                assert result["rollback"] == "automatic"

    @pytest.mark.asyncio
    async def test_apply_update_unsupported_service(self, backup_manager, temp_dirs):
        """Test update with unsupported service."""
        bin_dir, _ = temp_dirs

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            service = UpdateService(backup_manager=backup_manager)

            with pytest.raises(UpdateError, match="Unsupported service"):
                await service.apply_update(
                    service="unsupported",
                    version="v1.0.0",
                    binary_path=bin_dir / "test",
                )

    @pytest.mark.asyncio
    async def test_rollback_success(self, backup_manager, mock_health_checker, temp_dirs):
        """Test successful rollback."""
        bin_dir, backup_dir = temp_dirs

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
                binary_path = bin_dir / "llama-server"
                binary_path.write_bytes(b"current content")

                await backup_manager.create_backup("llama.cpp", "v1.0.0")

                binary_path.write_bytes(b"updated content")

                service = UpdateService(
                    backup_manager=backup_manager,
                    health_checker=mock_health_checker,
                )

                result = await service.rollback(service="llama.cpp")

                assert result["status"] == "success"
                assert result["version"] == "v1.0.0"

    @pytest.mark.asyncio
    async def test_rollback_no_backups(self, backup_manager):
        """Test rollback with no backups."""
        service = UpdateService(backup_manager=backup_manager)

        result = await service.rollback(service="llama.cpp")

        assert result["status"] == "failed"
        assert "No backups found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_status(self, backup_manager, temp_dirs):
        """Test getting update status."""
        bin_dir, backup_dir = temp_dirs

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
                binary_path = bin_dir / "llama-server"
                binary_path.write_bytes(b"test content")

                version_file = backup_dir / "versions.json"
                version_file.write_text(
                    json.dumps({"llama.cpp": {"version": "v1.0.0"}})
                )

                await backup_manager.create_backup("llama.cpp", "v1.0.0")

                service = UpdateService(backup_manager=backup_manager)
                status = await service.get_status()

                assert "services" in status
                assert "available_backups" in status


class TestIntegration:
    """Integration tests for update mechanism."""

    @pytest.mark.asyncio
    async def test_full_update_workflow(self, temp_dirs):
        """Test full update workflow: backup -> update -> rollback."""
        bin_dir, backup_dir = temp_dirs

        mock_health_checker = MagicMock()
        health_running = MagicMock()
        health_running.status = MagicMock()
        health_running.status.name = "RUNNING"
        mock_health_checker.check_llama = AsyncMock(return_value=health_running)
        mock_health_checker.check_qdrant = AsyncMock(return_value=health_running)

        with patch("src.admin.backup_manager.BIN_DIR", bin_dir):
            with patch("src.admin.backup_manager.BACKUP_DIR", backup_dir):
                binary_path = bin_dir / "llama-server"
                binary_path.write_bytes(b"original v1.0.0")

                version_file = backup_dir / "versions.json"
                version_file.write_text(
                    json.dumps({"llama.cpp": {"version": "v1.0.0"}})
                )

                backup_manager = BackupManager(
                    backup_dir=backup_dir,
                    max_backups=3,
                )

                backup = await backup_manager.create_backup(
                    "llama.cpp", "v1.0.0"
                )
                assert backup.version == "v1.0.0"

                binary_path.write_bytes(b"updated v1.1.0")
                await backup_manager.update_version_metadata("llama.cpp", "v1.1.0")

                version = backup_manager.get_current_version("llama.cpp")
                assert version == "v1.1.0"

                update_service = UpdateService(
                    backup_manager=backup_manager,
                    health_checker=mock_health_checker,
                )

                result = await update_service.rollback("llama.cpp")
                assert result["status"] == "success"