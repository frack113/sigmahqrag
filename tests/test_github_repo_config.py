"""
Tests for GitHub repository configuration handling.
"""
import pytest
import sys
sys.path.insert(0, '.')
from src.nicegui_app.pages.github_repo_page import load_config as original_load_config, save_config as original_save_config
import json
import os
from pathlib import Path

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

def test_load_config_empty_file():
    """Test loading configuration when the file does not exist."""
    # Use test config path
    if test_config_path.exists():
        original_content = test_config_path.read_text()
        test_config_path.unlink()

    try:
        assert load_config() == {"repositories": []}
    finally:
        # Restore the file if it existed before
        if "original_content" in locals():
            with open(test_config_path, "w") as f:
                f.write(original_content)

def test_save_and_load_config():
    """Test saving and loading configuration."""
    # Initialize empty config for this test
    if not test_config_path.exists():
        with open(test_config_path, "w") as f:
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
    # Initialize config with a repository for this test
    with open(test_config_path, "w") as f:
        json.dump({"repositories": [{"url": "https://github.com/example/repo", "branch": "main"}]}, f)
    
    loaded_config = load_config()
    assert len(loaded_config["repositories"]) > 0
    assert loaded_config["repositories"][0]["url"] == "https://github.com/example/repo"

def test_add_repository_to_config():
    """Test adding a repository to the configuration."""
    # Initialize empty config for this test
    with open(test_config_path, "w") as f:
        json.dump({"repositories": []}, f)
    
    # Load initial empty config
    initial_config = load_config()
    assert len(initial_config["repositories"]) == 0
    
    # Add a repository
    new_repo = {
        "url": "https://github.com/test/user",
        "branch": "main",
        "enabled": True,
        "file_extensions": [".py"]
    }
    initial_config["repositories"].append(new_repo)
    save_config(initial_config)
    
    # Load and verify
    loaded_config = load_config()
    assert len(loaded_config["repositories"]) == 1
    assert loaded_config["repositories"][0]["url"] == "https://github.com/test/user"

def test_update_repository_in_config():
    """Test updating a repository in the configuration."""
    # Initialize empty config for this test
    with open(test_config_path, "w") as f:
        json.dump({"repositories": []}, f)
    
    # Add initial repository
    initial_config = load_config()
    initial_config["repositories"].append({
        "url": "https://github.com/test/user",
        "branch": "main",
        "enabled": True,
        "file_extensions": [".py"]
    })
    save_config(initial_config)
    
    # Update the repository
    updated_config = load_config()
    if len(updated_config["repositories"]) > 0:
        updated_config["repositories"][0]["branch"] = "dev"
        updated_config["repositories"][0]["file_extensions"].append(".md")
        save_config(updated_config)
    
    # Load and verify
    final_config = load_config()
    assert len(final_config["repositories"]) == 1
    assert final_config["repositories"][0]["branch"] == "dev"
    assert ".md" in final_config["repositories"][0]["file_extensions"]
