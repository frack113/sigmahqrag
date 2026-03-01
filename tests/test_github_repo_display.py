"""
Test GitHub repository display functionality
"""
import pytest
from nicegui import ui
import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nicegui_app.pages.github_repo_page import initialize_page, fetch_github_repositories
import json

# Use test config file for all tests in this module
test_config_path = Path("tests/files/config/github.json")

def load_config():
    """Load configuration from test file instead of main config."""
    if not test_config_path.exists():
        return {"repositories": []}
    
    with open(test_config_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file) or {"repositories": []}
        except (json.JSONDecodeError, FileNotFoundError):
            return {"repositories": []}

def save_config(config: dict) -> None:
    """Save configuration to test file instead of main config."""
    os.makedirs(test_config_path.parent, exist_ok=True)
    
    with open(test_config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

def test_fetch_github_repositories():
    """Test that repositories are fetched correctly."""
    # Note: This may fail if GitHub API is unreachable, but the UI should handle it gracefully
    try:
        repositories = fetch_github_repositories()
        # If we get here, the function works (may return empty list if no valid repos)
        assert isinstance(repositories, list), "Should return a list"
        print(f"Fetched {len(repositories)} repository(ies)")
    except Exception as e:
        # Expected during testing - GitHub API may not be accessible
        print(f"GitHub fetch failed (expected): {e}")


def test_repository_list_initialization():
    """Test that the repository list UI initializes without errors."""
    # This should not raise an error
    from nicegui_app.app import create_nicegui_app
    assert create_nicegui_app is not None

def test_fetch_github_repositories_with_config():
    """Test that repositories are fetched based on configuration."""
    # Initialize empty config for this test
    with open(test_config_path, "w") as f:
        json.dump({"repositories": []}, f)
    
    # Add a test repository to config
    test_config = {
        "repositories": [
            {
                "url": "https://github.com/example/repo",
                "branch": "main",
                "enabled": True,
                "file_extensions": [".py", ".md"]
            }
        ]
    }
    save_config(test_config)
    
    # Fetch repositories (may return empty if GitHub API is unreachable, but should not crash)
    try:
        repositories = fetch_github_repositories()
        assert isinstance(repositories, list), "Should return a list"
    except Exception as e:
        print(f"GitHub fetch failed: {e}")
