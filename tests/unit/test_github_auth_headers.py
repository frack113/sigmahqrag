"""Tests for GitHub token auto-discovery in VersionManager."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.shared.version_manager import VersionManager


class TestGitHubTokenDiscovery:
    def test_token_from_env_var(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}, clear=True):
            vm = VersionManager()
            headers = vm._get_headers()
            assert headers.get("Authorization") == "Bearer ghp_test123"

    def test_token_from_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text("GITHUB_TOKEN=ghp_dotenv_token\nOTHER_KEY=value\n")
        monkeypatch.chdir(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            vm = VersionManager()
            headers = vm._get_headers()
            assert headers.get("Authorization") == "Bearer ghp_dotenv_token"

    def test_missing_token_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level("WARNING")
        with patch.dict(os.environ, {}, clear=True):
            vm = VersionManager()
            headers = vm._get_headers()
            assert "Authorization" not in headers
            assert "No GitHub token found" in caplog.text

    def test_token_respects_explicit_param(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_env"}, clear=True):
            vm = VersionManager(github_token="ghp_explicit")
            headers = vm._get_headers()
            assert headers.get("Authorization") == "Bearer ghp_explicit"

    def test_token_from_dotenv_with_quotes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        dotenv = tmp_path / ".env"
        dotenv.write_text('GITHUB_TOKEN="ghp_quoted_token"\n')
        monkeypatch.chdir(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            vm = VersionManager()
            headers = vm._get_headers()
            assert headers.get("Authorization") == "Bearer ghp_quoted_token"
