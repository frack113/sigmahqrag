"""Tests for init-projet.py script."""

import tempfile
from pathlib import Path
import sys
import os

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original_cwd)


def test_data_structure_created(temp_project_dir):
    """Test that all required data directories are created."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import create_data_structure, DATA_DIRS

    create_data_structure()

    for d in DATA_DIRS:
        assert Path(d).exists(), f"Directory {d} was not created"
        assert Path(d).is_dir(), f"{d} is not a directory"


def test_config_file_created_no_backend_section(temp_project_dir):
    """Test that sigmarag.toml is created at root without [backend] section."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import create_config_file, CONFIG_FILE

    create_config_file()

    assert CONFIG_FILE.exists(), "Config file was not created"
    content = CONFIG_FILE.read_text(encoding="utf-8")
    assert "[backend]" not in content, "Config should not contain [backend] section"
    assert "[services.llama]" in content
    assert "[services.qdrant]" in content
    assert "[logging]" in content
    assert "[rag]" in content


def test_config_file_not_overwritten(temp_project_dir):
    """Test that existing config file is not overwritten."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import create_config_file, CONFIG_FILE

    # Create a custom config first
    custom_content = '[custom]\nkey = "value"\n'
    CONFIG_FILE.write_text(custom_content, encoding="utf-8")

    create_config_file()

    # Should preserve custom content
    content = CONFIG_FILE.read_text(encoding="utf-8")
    assert content == custom_content, "Existing config should not be overwritten"


def test_init_file_format(temp_project_dir):
    """Test that init.txt contains correct format with ISO 8601 timestamp."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import create_init_file, INIT_FILE

    create_init_file()

    assert INIT_FILE.exists(), "init.txt was not created"
    content = INIT_FILE.read_text(encoding="utf-8").strip()
    assert content.startswith("Init data structure the "), "Invalid prefix"

    # Extract timestamp and verify ISO 8601 format
    timestamp_str = content.replace("Init data structure the ", "")
    # Should parse as valid ISO 8601
    from datetime import datetime

    parsed = datetime.fromisoformat(timestamp_str)
    assert parsed is not None


def test_init_file_unique_timestamp(temp_project_dir):
    """Test that each run creates a unique timestamp."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import create_init_file, INIT_FILE
    import time

    create_init_file()
    content1 = INIT_FILE.read_text(encoding="utf-8").strip()

    time.sleep(0.01)  # Ensure different timestamp

    create_init_file()
    content2 = INIT_FILE.read_text(encoding="utf-8").strip()

    assert content1 != content2, "Timestamps should be different"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
