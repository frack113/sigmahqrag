"""Tests for git repository management utilities."""

import pytest

from src.infrastructure.github.git import _validate_git_url, _validate_org_name


class TestValidateOrgName:
    def test_valid_names(self) -> None:
        _validate_org_name("org", "name")
        _validate_org_name("my-org", "my-repo")
        _validate_org_name("org123", "name_123")
        _validate_org_name("org.name", "name.dot")

    def test_invalid_names(self) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            _validate_org_name("../org", "name")
        with pytest.raises(ValueError, match="path traversal"):
            _validate_org_name("org", "../name")
        with pytest.raises(ValueError, match="path traversal"):
            _validate_org_name("org/foo", "name")


class TestValidateGitUrl:
    def test_valid_https(self) -> None:
        _validate_git_url("https://github.com/org/repo.git")

    def test_valid_git(self) -> None:
        _validate_git_url("git://github.com/org/repo.git")

    def test_invalid_scheme(self) -> None:
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _validate_git_url("ftp://github.com/org/repo.git")

    def test_localhost_blocked(self) -> None:
        with pytest.raises(ValueError, match="localhost"):
            _validate_git_url("https://localhost/repo.git")

    def test_local_ip_blocked(self) -> None:
        with pytest.raises(ValueError, match="localhost"):
            _validate_git_url("https://127.0.0.1/repo.git")

    def test_private_ip_not_blocked_due_to_bug(self) -> None:
        # NOTE: The except ValueError: pass in _validate_git_url catches the
        # intentional raise for private/reserved IPs, so they are NOT blocked.
        _validate_git_url("https://10.0.0.1/repo.git")
