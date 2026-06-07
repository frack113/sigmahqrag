"""Advanced tests for git repository management."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.github.git import (
    _get_repo_key,
    _get_repo_path,
    _is_valid_repo,
    get_last_commit_date,
    get_selected_dirs,
    is_repo_outdated,
    list_directory_tree,
    save_metadata,
    save_selected_dirs,
)


class TestGetRepoPath:
    def test_returns_correct_path(self, tmp_path: Path) -> None:
        result = _get_repo_path(tmp_path, "my-org", "my-repo")
        assert result == tmp_path / "my-org" / "my-repo"

    def test_validates_org_name(self) -> None:
        with pytest.raises(ValueError):
            _get_repo_path(Path("/tmp"), "../org", "repo")


class TestIsValidRepo:
    def test_valid_repo(self) -> None:
        with patch("src.infrastructure.github.git.Repo") as MockRepo:
            assert _is_valid_repo(Path("/repo")) is True
            MockRepo.assert_called_once_with(Path("/repo"))

    def test_invalid_repo(self) -> None:
        from git.exc import InvalidGitRepositoryError

        with patch("src.infrastructure.github.git.Repo", side_effect=InvalidGitRepositoryError):
            assert _is_valid_repo(Path("/invalid")) is False


class TestListDirectoryTree:
    def test_returns_empty_for_nonexistent(self) -> None:
        result = list_directory_tree("org", "repo", repos_dir=Path("/nonexistent"))
        assert result == []

    def test_lists_directories(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "org" / "repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("")
        (repo_path / "docs").mkdir()
        (repo_path / "docs" / "readme.md").write_text("")

        with patch("src.infrastructure.github.git._is_valid_repo", return_value=True):
            result = list_directory_tree("org", "repo", repos_dir=tmp_path, max_depth=3)
            names = [n["name"] for n in result]
            assert "src" in names
            assert "docs" in names

    def test_skips_hidden_dirs(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "org" / "repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        (repo_path / ".hidden").mkdir()
        (repo_path / "visible").mkdir()

        with patch("src.infrastructure.github.git._is_valid_repo", return_value=True):
            result = list_directory_tree("org", "repo", repos_dir=tmp_path)
            names = [n["name"] for n in result]
            assert "visible" in names
            assert ".hidden" not in names
            assert ".git" not in names

    def test_respects_max_depth(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "org" / "repo"
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        deep = repo_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "d").mkdir()

        with patch("src.infrastructure.github.git._is_valid_repo", return_value=True):
            result = list_directory_tree("org", "repo", repos_dir=tmp_path, max_depth=1)
            names = [n["name"] for n in result]
            assert "a" in names
            if names:
                children_a = result[names.index("a")].get("children", [])
                if children_a:
                    assert len(children_a) == 0 or "b" not in [ch["name"] for ch in children_a]


class TestGetRepoKey:
    def test_returns_org_slash_name(self) -> None:
        assert _get_repo_key("org", "name") == "org/name"


class TestSaveMetadata:
    def test_calls_db(self) -> None:
        mock_db = MagicMock()
        with patch(
            "src.infrastructure.github.git.DatabaseService.get_instance", return_value=mock_db
        ):
            save_metadata("org", "repo", {"key": "val"})
            mock_db.set_git_metadata.assert_called_once_with("org/repo", {"key": "val"})


class TestSaveSelectedDirs:
    def test_saves_successfully(self) -> None:
        mock_db = MagicMock()
        with patch(
            "src.infrastructure.github.git.DatabaseService.get_instance", return_value=mock_db
        ):
            result = save_selected_dirs("org", "repo", ["src/", "docs/"])
            assert result["success"] is True
            mock_db.set_selected_dirs.assert_called_once_with("org/repo", ["src/", "docs/"])

    def test_handles_exception(self) -> None:
        mock_db = MagicMock()
        mock_db.set_selected_dirs.side_effect = RuntimeError("db fail")
        with patch(
            "src.infrastructure.github.git.DatabaseService.get_instance", return_value=mock_db
        ):
            result = save_selected_dirs("org", "repo", ["src/"])
            assert result["success"] is False


class TestGetSelectedDirs:
    def test_returns_dirs(self) -> None:
        mock_db = MagicMock()
        mock_db.get_selected_dirs.return_value = ["src/"]
        with patch(
            "src.infrastructure.github.git.DatabaseService.get_instance", return_value=mock_db
        ):
            result = get_selected_dirs("org", "repo")
            assert result == ["src/"]

    def test_handles_exception(self) -> None:
        mock_db = MagicMock()
        mock_db.get_selected_dirs.side_effect = RuntimeError("fail")
        with patch(
            "src.infrastructure.github.git.DatabaseService.get_instance", return_value=mock_db
        ):
            result = get_selected_dirs("org", "repo")
            assert result == []


class TestGetLastCommitDate:
    def test_returns_none_for_missing_repo(self) -> None:
        from git.exc import InvalidGitRepositoryError

        with patch("src.infrastructure.github.git.Repo", side_effect=InvalidGitRepositoryError):
            result = get_last_commit_date("org", "repo", repos_dir=Path("/tmp"))
            assert result is None


class TestIsRepoOutdated:
    def test_returns_false_for_missing_repo(self) -> None:
        from git.exc import InvalidGitRepositoryError

        with patch("src.infrastructure.github.git.Repo", side_effect=InvalidGitRepositoryError):
            result = is_repo_outdated("org", "repo", repos_dir=Path("/tmp"))
            assert result is False
