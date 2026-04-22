"""Custom exceptions for SigmaHQ RAG."""


class SigmaError(Exception):
    """Base exception for Sigma errors."""

    def __init__(
        self, code: str, message: str, details: dict[str, str] | None = None
    ) -> None:
        """Initialize exception."""
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ServiceUnavailableError(SigmaError):
    """Service unavailable error."""

    def __init__(self, service: str) -> None:
        """Initialize exception."""
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=f"Service unavailable: {service}",
            details={"service": service},
        )


class ModelNotFoundError(SigmaError):
    """Model not found error."""

    def __init__(self, model_name: str) -> None:
        """Initialize exception."""
        super().__init__(
            code="MODEL_NOT_FOUND",
            message=f"Model not found: {model_name}",
            details={"model_name": model_name},
        )


class ValidationError(SigmaError):
    """Validation error."""

    def __init__(self, field: str, message: str) -> None:
        """Initialize exception."""
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details={"field": field},
        )
