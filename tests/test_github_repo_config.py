"""
Tests for GitHub repository configuration handling.
"""
import pytest
import sys
sys.path.insert(0, '.')
from src.nicegui_app.pages.github_repo_page import load_config, save_config
import json
import os
from pathlib import Path

def test_load_config_empty_file():
    """Test loading configuration when the file does not exist."""
    config_path = Path("config/github.json")
    if config_path.exists():
        original_content = config_path.read_text()
        config_path.unlink()

    try:
        assert load_config() == {"repositories": []}
    finally:
        # Restore the file if it existed before
        if "original_content" in locals():
            with open(config_path, "w") as f:
                f.write(original_content)

def test_save_and_load_config():
    """Test saving and loading configuration."""
    config_path = Path("config/github.json")
    if not config_path.exists():
        with open(config_path, "w") as f:
            json.dump({"repositories": []}, f)

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
    loaded_config = load_config()
    assert loaded_config == test_config

def test_load_config_with_existing_file():
    """Test loading configuration from an existing file."""
    config_path = Path("config/github.json")
    if not config_path.exists():
        with open(config_path, "w") as f:
            json.dump({"repositories": [{"url": "https://github.com/example/repo", "branch": "main"}]}, f)
    
    loaded_config = load_config()
    assert len(loaded_config["repositories"]) > 0
    assert loaded_config["repositories"][0]["url"] == "https://github.com/example/repo"
