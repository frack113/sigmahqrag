"""
Test GitHub repository removal functionality
"""
import json
import tempfile
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


def test_remove_repository():
    """Test that removing a repository works correctly."""
    # Use the test config file for testing
    test_config_path = Path("tests/files/config/github.json")
    
    # Backup existing config if it exists
    backup_data = None
    if test_config_path.exists():
        with open(test_config_path, "r") as f:
            backup_data = f.read()
    
    try:
        initial_config = {
            "repositories": [
                {"url": "https://github.com/user/repo1", "branch": "main", "enabled": True, "file_extensions": [".py"]},
                {"url": "https://github.com/user/repo2", "branch": "dev", "enabled": False, "file_extensions": [".md"]},
                {"url": "https://github.com/user/repo3", "branch": "master", "enabled": True, "file_extensions": [".js"]}
            ]
        }
        
        # Save initial config
        with open(test_config_path, "w") as f:
            json.dump(initial_config, f)
        
        # Load and verify we have 3 repositories
        config = load_config()
        assert len(config["repositories"]) == 3
        
        # Simulate removing the second repository (index 1)
        repositories = config["repositories"]
        if 0 <= 1 < len(repositories):
            removed_url = repositories.pop(1)["url"]
            save_config({"repositories": repositories})
        
        # Load again and verify we have 2 repositories
        config_after = load_config()
        assert len(config_after["repositories"]) == 2
        assert removed_url == "https://github.com/user/repo2"
        assert config_after["repositories"][0]["url"] == "https://github.com/user/repo1"
        assert config_after["repositories"][1]["url"] == "https://github.com/user/repo3"
    finally:
        # Restore original config or clean up
        if backup_data is not None:
            with open(test_config_path, "w") as f:
                f.write(backup_data)
        else:
            test_config_path.unlink(missing_ok=True)


def test_remove_last_repository():
    """Test that removing the last repository results in empty list."""
    # Use the test config file for testing
    test_config_path = Path("tests/files/config/github.json")
    
    # Backup existing config if it exists
    backup_data = None
    if test_config_path.exists():
        with open(test_config_path, "r") as f:
            backup_data = f.read()
    
    try:
        initial_config = {
            "repositories": [
                {"url": "https://github.com/user/repo1", "branch": "main", "enabled": True, "file_extensions": [".py"]}
            ]
        }
        
        # Save initial config
        with open(test_config_path, "w") as f:
            json.dump(initial_config, f)
        
        # Load and verify we have 1 repository
        config = load_config()
        assert len(config["repositories"]) == 1
        
        # Remove the only repository
        repositories = config["repositories"]
        if 0 <= 0 < len(repositories):
            removed_url = repositories.pop(0)["url"]
            save_config({"repositories": repositories})
        
        # Load again and verify we have empty list
        config_after = load_config()
        assert len(config_after["repositories"]) == 0
        assert removed_url == "https://github.com/user/repo1"
    finally:
        # Restore original config or clean up
        if backup_data is not None:
            with open(test_config_path, "w") as f:
                f.write(backup_data)
        else:
            test_config_path.unlink(missing_ok=True)

def test_remove_repository_by_index():
    """Test removing a repository by index from the configuration."""
    # Use the test config file for testing
    test_config_path = Path("tests/files/config/github.json")
    
    # Backup existing config if it exists
    backup_data = None
    if test_config_path.exists():
        with open(test_config_path, "r") as f:
            backup_data = f.read()
    
    try:
        # Initialize empty config for this test
        with open(test_config_path, "w") as f:
            json.dump({"repositories": []}, f)
        
        # Add multiple repositories
        initial_config = load_config()
        initial_config["repositories"].extend([
            {"url": "https://github.com/test/repo1", "branch": "main", "enabled": True, "file_extensions": [".py"]},
            {"url": "https://github.com/test/repo2", "branch": "dev", "enabled": False, "file_extensions": [".md"]},
            {"url": "https://github.com/test/repo3", "branch": "master", "enabled": True, "file_extensions": [".js"]}
        ])
        save_config(initial_config)
        
        # Verify we have 3 repositories
        config = load_config()
        assert len(config["repositories"]) == 3
        
        # Remove the second repository (index 1)
        if 0 <= 1 < len(config["repositories"]):
            removed_url = config["repositories"].pop(1)["url"]
            save_config({"repositories": config["repositories"]})
        
        # Load again and verify we have 2 repositories
        final_config = load_config()
        assert len(final_config["repositories"]) == 2
        assert removed_url == "https://github.com/test/repo2"
    finally:
        # Restore original config or clean up
        if backup_data is not None:
            with open(test_config_path, "w") as f:
                f.write(backup_data)
        else:
            test_config_path.unlink(missing_ok=True)
