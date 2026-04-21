"""Pytest fixtures."""

import pytest
from typing import Any


@pytest.fixture
def sample_sigma_rule() -> dict[str, Any]:
    """Sample Sigma rule."""
    return {
        "id": "test-rule-001",
        "title": "Test Rule",
        "detection": {"condition": "test"},
        "status": "stable",
        "level": "medium",
    }


@pytest.fixture
def sample_documents() -> list[dict[str, Any]]:
    """Sample documents."""
    return [
        {"id": "1", "text": "Document 1"},
        {"id": "2", "text": "Document 2"},
    ]