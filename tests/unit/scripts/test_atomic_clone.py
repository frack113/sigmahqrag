"""Tests for atomic clone behavior and git error handling."""

import tempfile
from pathlib import Path
import sys
import os
from unittest.mock import MagicMock, patch, call

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original_cwd)


def test_atomic_clone_no_partial_dir_on_failure(temp_project_dir):
    """Test that failed clone doesn't leave partial directory in data/."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from setup import clone_or_update_sigma_spec, SIGMA_SPEC_DIR
    from git.exc import GitCommandError

    # Ensure no existing directory
    if SIGMA_SPEC_DIR.exists():
        import shutil

        shutil.rmtree(SIGMA_SPEC_DIR)

    # Mock clone_from to fail
    with patch("setup.git.Repo.clone_from") as mock_clone:
        mock_clone.side_effect = GitCommandError("clone", "Network error")

        with pytest.raises(SystemExit):
            clone_or_update_sigma_spec()

        # Verify no directory was created in data/
        assert not SIGMA_SPEC_DIR.exists()


def test_atomic_clone_uses_temp_dir(temp_project_dir):
    """Test that clone uses temporary directory before moving."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from setup import clone_or_update_sigma_spec, SIGMA_SPEC_DIR

    # Ensure no existing directory
    if SIGMA_SPEC_DIR.exists():
        import shutil

        shutil.rmtree(SIGMA_SPEC_DIR)

    with (
        patch("setup.git.Repo.clone_from") as mock_clone,
        patch("setup.shutil.move") as mock_move,
        patch("setup.tempfile.TemporaryDirectory") as mock_tempdir,
    ):
        mock_tempdir.return_value.__enter__.return_value = "/tmp/fake-temp"
        mock_tempdir.return_value.__exit__.return_value = None

        # Mock successful clone
        mock_clone.return_value = MagicMock()

        clone_or_update_sigma_spec()

        # Verify clone_from was called
        mock_clone.assert_called_once()
        # Verify move was called (atomic move)
        mock_move.assert_called_once()
        # Verify temp directory was used
        mock_tempdir.assert_called_once()


@pytest.mark.parametrize(
    "scenario",
    [
        "pull_fails_then_recover",
        "stash_fails_then_recover",
    ],
)
def test_git_update_recovers_from_errors(temp_project_dir, scenario):
    """Test that git update recovers from various errors via fetch+reset."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from setup import clone_or_update_sigma_spec, SIGMA_SPEC_DIR
    from git.exc import GitCommandError
    from unittest.mock import MagicMock

    # Setup existing repo with .git directory
    SIGMA_SPEC_DIR.parent.mkdir(parents=True, exist_ok=True)
    SIGMA_SPEC_DIR.mkdir()
    (SIGMA_SPEC_DIR / ".git").mkdir()
    (SIGMA_SPEC_DIR / ".git" / "config").write_text("[core]\nrepositoryformatversion = 0\n")

    with patch("setup.git.Repo") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.is_dirty.return_value = scenario == "stash_fails_then_recover"

        # First pull fails
        mock_repo.remotes.origin.pull.side_effect = GitCommandError("pull", "Network error")
        # But fetch succeeds
        mock_repo.remotes.origin.fetch.return_value = None
        # And reset succeeds
        mock_repo.git.reset.return_value = None

        # Should not raise - recovers via fetch+reset
        clone_or_update_sigma_spec()

        # Verify recovery path was taken
        mock_repo.remotes.origin.fetch.assert_called_once()
        mock_repo.git.reset.assert_called_once_with("--hard", "origin/main")


def test_git_update_fails_when_recovery_fails(temp_project_dir):
    """Test that git update fails when both pull and fetch+reset fail."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from setup import clone_or_update_sigma_spec, SIGMA_SPEC_DIR
    from git.exc import GitCommandError
    from unittest.mock import MagicMock

    # Setup existing repo
    SIGMA_SPEC_DIR.parent.mkdir(parents=True, exist_ok=True)
    SIGMA_SPEC_DIR.mkdir()
    (SIGMA_SPEC_DIR / ".git").mkdir()
    (SIGMA_SPEC_DIR / ".git" / "config").write_text("[core]\nrepositoryformatversion = 0\n")

    with patch("setup.git.Repo") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.is_dirty.return_value = False

        # Both pull and fetch fail
        mock_repo.remotes.origin.pull.side_effect = GitCommandError("pull", "Network error")
        mock_repo.remotes.origin.fetch.side_effect = GitCommandError("fetch", "Network error")

        with pytest.raises(SystemExit):
            clone_or_update_sigma_spec()


def test_clone_retries_with_backoff(temp_project_dir):
    """Test that clone retries with exponential backoff on transient failures."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from setup import clone_or_update_sigma_spec, SIGMA_SPEC_DIR
    from git.exc import GitCommandError

    # Ensure no existing directory
    if SIGMA_SPEC_DIR.exists():
        import shutil

        shutil.rmtree(SIGMA_SPEC_DIR)

    # Mock clone_from to fail twice then succeed
    call_count = 0

    def mock_clone(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise GitCommandError("clone", "Transient network error")
        # On third call, create a fake repo structure
        temp_dir = Path(args[1])
        temp_dir.mkdir(parents=True)
        (temp_dir / ".git").mkdir()
        (temp_dir / ".git" / "config").write_text("[core]\nrepositoryformatversion = 0\n")
        return MagicMock()

    with (
        patch("setup.git.Repo.clone_from", side_effect=mock_clone) as mock_clone,
        patch("setup.time.sleep") as mock_sleep,
    ):
        clone_or_update_sigma_spec()

        assert call_count == 3
        assert mock_sleep.call_count == 2  # 2 retries = 2 sleeps
        # Verify exponential backoff: 2s, 4s
        mock_sleep.assert_has_calls([call(2), call(4)])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
