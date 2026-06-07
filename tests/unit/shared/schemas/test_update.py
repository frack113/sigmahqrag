"""Tests for update schemas."""

from datetime import datetime

from src.application.system.schemas import (
    BackupInfo,
    ServiceVersionInfo,
    UpdateApplyRequest,
    UpdateApplyResponse,
    UpdateRollbackRequest,
    UpdateRollbackResponse,
    UpdateStatus,
    create_apply_response,
    create_rollback_response,
)


class TestUpdateApplyRequest:
    def test_fields(self) -> None:
        req = UpdateApplyRequest(service="llama.cpp", version="b1234")
        assert req.service == "llama.cpp"
        assert req.version == "b1234"


class TestUpdateApplyResponse:
    def test_minimal(self) -> None:
        resp = UpdateApplyResponse(status="success", service="llama.cpp", version="b1234")
        assert resp.previous_version is None

    def test_full(self) -> None:
        resp = UpdateApplyResponse(
            status="failed",
            service="qdrant",
            version="v1.0",
            previous_version="v0.9",
            error="something broke",
        )
        assert resp.error == "something broke"


class TestUpdateRollbackRequest:
    def test_fields(self) -> None:
        req = UpdateRollbackRequest(service="qdrant")
        assert req.service == "qdrant"


class TestUpdateRollbackResponse:
    def test_fields(self) -> None:
        resp = UpdateRollbackResponse(status="success", service="qdrant")
        assert resp.version is None

    def test_with_version(self) -> None:
        resp = UpdateRollbackResponse(
            status="success", service="qdrant", version="v1.0", health_check="ok"
        )
        assert resp.health_check == "ok"


class TestServiceVersionInfo:
    def test_fields(self) -> None:
        info = ServiceVersionInfo(current_version="b1234")
        assert info.last_updated is None

    def test_with_last_updated(self) -> None:
        dt = datetime(2024, 1, 1)
        info = ServiceVersionInfo(current_version="b1234", last_updated=dt)
        assert info.last_updated == dt


class TestBackupInfo:
    def test_fields(self) -> None:
        dt = datetime(2024, 6, 15)
        info = BackupInfo(name="backup1", path="/tmp/bk", size=1024, created_at=dt)
        assert info.size == 1024


class TestUpdateStatus:
    def test_fields(self) -> None:
        llama = ServiceVersionInfo(current_version="b1234")
        qdrant = ServiceVersionInfo(current_version="v1.0")
        status = UpdateStatus(llama_cpp=llama, qdrant=qdrant)
        assert status.llama_cpp.current_version == "b1234"
        assert status.available_backups == []


class TestCreateApplyResponse:
    def test_minimal(self) -> None:
        result = create_apply_response("success", "llama.cpp", "b1234")
        assert result["status"] == "success"
        assert "error" not in result

    def test_full(self) -> None:
        result = create_apply_response(
            "failed", "qdrant", "v1.0", previous_version="v0.9", error="broken"
        )
        assert result["error"] == "broken"

    def test_with_health_check_rollback(self) -> None:
        result = create_apply_response(
            "success",
            "llama.cpp",
            "b1234",
            previous_version="b1233",
            health_check="ok",
            rollback="none",
        )
        assert result["health_check"] == "ok"
        assert result["rollback"] == "none"


class TestCreateRollbackResponse:
    def test_minimal(self) -> None:
        result = create_rollback_response("success", "qdrant")
        assert result["status"] == "success"

    def test_with_version(self) -> None:
        result = create_rollback_response("success", "qdrant", version="v1.0")
        assert result["version"] == "v1.0"

    def test_with_health_check_error(self) -> None:
        result = create_rollback_response(
            "failed", "qdrant", version="v0.9", health_check="ko", error="broken"
        )
        assert result["health_check"] == "ko"
        assert result["error"] == "broken"
