"""Pytest fixtures."""

from typing import Any

import pytest


@pytest.fixture
def sample_sigma_rule() -> dict[str, Any]:
    """Sample Sigma rule (Amelia suggestion)."""
    return {
        "title": "Suspicious PowerShell Execution",
        "detection": {
            "selection": {"Image": "powershell.exe"},
            "condition": "selection",
        },
        "logsource": {"category": "process_creation", "product": "windows"},
        "id": "test-rule-001",
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


@pytest.fixture
def valid_sigma_rule_yml() -> str:
    """Valid Sigma rule YAML content (Amelia suggestion)."""
    return """title: Suspicious PowerShell Execution
detection:
  selection:
    Image: powershell.exe
  condition: selection
logsource:
  category: process_creation
  product: windows
id: test-rule-001
status: stable
level: medium
"""
