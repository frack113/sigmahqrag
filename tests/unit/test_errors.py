"""Test custom exceptions."""

from src.errors import ModelNotFoundError, SigmaError, ValidationError


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
