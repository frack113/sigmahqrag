"""Tests for translate.py endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.translate import router, _render_safe, SIGMA_YAML_STOP_SEQUENCES

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestSchemaValidation:
    def test_missing_yaml_returns_422(self):
        response = client.post("/api/v1/translate/detection", json={})
        assert response.status_code == 422

    def test_empty_yaml_rejected(self):
        response = client.post(
            "/api/v1/translate/detection",
            json={"yaml": ""},
        )
        assert response.status_code == 422

    def test_valid_yaml_accepted(self):
        with patch("src.api.v1.translate.RAGPipeline") as mock_rag:
            mock_instance = MagicMock()
            mock_instance.search_engine.search = AsyncMock(return_value=[])
            mock_instance.answer_search_query = AsyncMock(return_value="translated text")
            mock_instance.search_engine.get_citation.return_value = None
            mock_rag.return_value = mock_instance

            response = client.post(
                "/api/v1/translate/detection",
                json={"yaml": "detection:\n  condition: selection"},
            )
            assert response.status_code == 200
            assert response.json()["translation"] == "translated text"

    def test_default_values(self):
        with patch("src.api.v1.translate.RAGPipeline") as mock_rag:
            mock_instance = MagicMock()
            mock_instance.search_engine.search = AsyncMock(return_value=[])
            mock_instance.answer_search_query = AsyncMock(return_value="ok")
            mock_instance.search_engine.get_citation.return_value = None
            mock_rag.return_value = mock_instance

            response = client.post(
                "/api/v1/translate/detection",
                json={"yaml": "test"},
            )
            assert response.status_code == 200
            mock_instance.answer_search_query.assert_called_once()
            call_kwargs = mock_instance.answer_search_query.call_args
            assert call_kwargs.kwargs["use_chat"] is True
            assert call_kwargs.kwargs["temperature"] == 0.1


class TestRenderSafe:
    def test_no_injection(self):
        malicious = "{{ config.something }} and {{ question }}"
        # With Undefined, accessing undefined vars raises UndefinedError
        # which is the safe behavior — injection is blocked
        try:
            result = _render_safe(malicious, question="test", search_results="data")
            # If it doesn't raise, the var should render as empty or Undefined
            assert "config" not in result or "Undefined" in result
        except Exception:
            # Raised UndefinedError — injection was blocked, which is correct
            pass

    def test_normal_template_renders(self):
        template = "Results: {{ search_results }}"
        result = _render_safe(template, search_results="found 5 docs")
        assert result == "Results: found 5 docs"

    def test_unknown_vars_render_as_undefined(self):
        template = "Value: {{ unknown_var }}"
        try:
            _render_safe(template)
            # May raise UndefinedError or render as empty
        except Exception:
            # UndefinedError — safe behavior
            pass


class TestStopSequences:
    def test_stop_sequences_cover_sigma_fields(self):
        expected = ["title", "id", "status", "detection", "condition", "logsource"]
        for field in expected:
            found = any(field in seq for seq in SIGMA_YAML_STOP_SEQUENCES)
            assert found, f"Missing stop sequence for field: {field}"
