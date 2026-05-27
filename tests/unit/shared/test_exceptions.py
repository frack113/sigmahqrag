"""Test custom exceptions."""

from src.shared.exceptions import (
    BackupError,
    DownloadError,
    ModelNotFoundError,
    ServiceUnavailableError,
    SigmaError,
    UpdateError,
    ValidationError,
)


def test_sigma_error() -> None:
    """Test SigmaError."""
    error = SigmaError(code="TEST", message="Test error")
    assert error.code == "TEST"
    assert error.message == "Test error"
    assert error.details == {}


def test_validation_error() -> None:
    """Test ValidationError."""
    error = ValidationError(field="field", message="Invalid")
    assert error.code == "VALIDATION_ERROR"
    assert error.details["field"] == "field"


def test_model_not_found_error() -> None:
    """Test ModelNotFoundError."""
    error = ModelNotFoundError(model_name="test-model")
    assert error.code == "MODEL_NOT_FOUND"
    assert error.details["model_name"] == "test-model"


def test_service_unavailable_error() -> None:
    """Test ServiceUnavailableError."""
    error = ServiceUnavailableError(service="qdrant")
    assert error.code == "SERVICE_UNAVAILABLE"
    assert error.http_status == 503
    assert error.details["service"] == "qdrant"


def test_download_error() -> None:
    """Test DownloadError."""
    error = DownloadError(message="download failed")
    assert error.code == "DOWNLOAD_ERROR"
    assert error.http_status == 500


def test_update_error() -> None:
    """Test UpdateError."""
    error = UpdateError(message="update failed")
    assert error.code == "UPDATE_ERROR"
    assert error.http_status == 500


def test_backup_error() -> None:
    """Test BackupError."""
    error = BackupError(message="backup failed")
    assert error.code == "BACKUP_ERROR"
    assert error.http_status == 500


def test_sigma_error_to_dict() -> None:
    """Test SigmaError.to_dict."""
    error = SigmaError(code="TEST", message="msg", details={"key": "val"})
    d = error.to_dict()
    assert d["code"] == "TEST"
    assert d["message"] == "msg"
    assert d["details"]["key"] == "val"
