"""Tests for error handling functionality."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.errors import (
    ModelNotFoundError,
    ServiceUnavailableError,
    SigmaError,
    ValidationError,
)


@pytest.fixture
def client() -> TestClient:
    """Create test client for the app."""
    from src.main import create_app

    app = create_app()
    return TestClient(app)


class TestHttpStatusProperty:
    """Tests for http_status property on exceptions."""

    def test_sigma_error_default_http_status(self) -> None:
        """Given SigmaError When instantiated Then http_status is 500."""
        exc = SigmaError(code="TEST", message="Test error")

        assert exc.http_status == 500

    def test_service_unavailable_http_status(self) -> None:
        """Given ServiceUnavailableError Then http_status is 503."""
        exc = ServiceUnavailableError("llama")

        assert exc.http_status == 503

    def test_model_not_found_http_status(self) -> None:
        """Given ModelNotFoundError Then http_status is 404."""
        exc = ModelNotFoundError("test-model")

        assert exc.http_status == 404

    def test_validation_error_http_status(self) -> None:
        """Given ValidationError Then http_status is 422."""
        exc = ValidationError(field="field", message="Invalid")

        assert exc.http_status == 422


class TestCorrelationID:
    """Tests for correlation ID middleware."""

    def test_correlation_id_header_present(
        self, client: TestClient
    ) -> None:
        """Given request When made Then X-Correlation-ID header present."""
        response = client.get("/health")

        assert "x-correlation-id" in response.headers

    def test_custom_correlation_id_used(
        self, client: TestClient
    ) -> None:
        """Given X-Correlation-ID header When provided Then uses it."""
        custom_id = "test-correlation-id-123"
        response = client.get(
            "/health",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.headers["x-correlation-id"] == custom_id


class TestExceptionHandlerIntegration:
    """Integration tests for exception handlers."""

    def test_sigma_error_handler_uses_http_status(
        self, client: TestClient
    ) -> None:
        """Given custom SigmaError raised When handled Then uses http_status property."""
        app = FastAPI()

        @app.exception_handler(SigmaError)
        async def sigma_handler(request, exc):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=exc.http_status,
                content=exc.to_dict(),
            )

        @app.get("/test")
        def test_endpoint():
            raise SigmaError("TEST_ERROR", "Test message", {})

        test_client = TestClient(app)
        response = test_client.get("/test")

        assert response.status_code == 500
        assert response.json()["code"] == "TEST_ERROR"

    def test_model_not_found_handler_uses_http_status(
        self, client: TestClient
    ) -> None:
        """Given ModelNotFoundError raised When handled Then uses 404."""
        app = FastAPI()

        @app.exception_handler(ModelNotFoundError)
        async def handler(request, exc):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=exc.http_status,
                content=exc.to_dict(),
            )

        @app.get("/test")
        def test_endpoint():
            raise ModelNotFoundError("missing-model")

        test_client = TestClient(app)
        response = test_client.get("/test")

        assert response.status_code == 404
        assert response.json()["code"] == "MODEL_NOT_FOUND"


class TestGenericExceptionHandler:
    """Tests for generic Exception handler."""

    def test_generic_exception_returns_clean_message(self) -> None:
        """Given unhandled exception When occurs Then returns 500 with clean message.

        This test verifies that when an uncaught exception occurs,
        the response does NOT expose internal error details.
        """
        from fastapi.testclient import TestClient

        from src.main import create_app

        app = create_app()

        @app.get("/raise-error")
        def raise_error():
            raise RuntimeError("Internal error details")

        test_client = TestClient(app, raise_server_exceptions=False)
        response = test_client.get("/raise-error")

        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "INTERNAL_ERROR"
        assert data["message"] == "An internal error occurred"
        assert "RuntimeError" not in data["message"]
        assert "traceback" not in data
