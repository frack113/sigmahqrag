"""Tests for init_projet.py script."""

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
    assert "[Hardware]" in content


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


def test_schema_version_set_in_database(temp_project_dir):
    """Test that schema_version is set in DuckDB config table after init."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import (
        create_data_structure,
        create_config_file,
        initialize_database,
        SCHEMA_VERSION,
    )
    from src.back.database import DatabaseService

    # Run init steps
    create_data_structure()
    create_config_file()
    # initialize_database creates and closes its own DB instance
    initialize_database()

    # Create a new DB instance to verify (since initialize_database closed it)
    db = DatabaseService()
    db.initialize()
    schema_version = db.get_config("schema_version")
    db.close()

    assert schema_version == SCHEMA_VERSION, (
        f"Expected schema_version {SCHEMA_VERSION}, got {schema_version}"
    )


def test_initialize_database_injectable(temp_project_dir):
    """Test that initialize_database accepts injected DatabaseService for testing."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from init_projet import initialize_database, DatabaseServiceProtocol
    from unittest.mock import MagicMock

    # Create mock database service with all required methods
    mock_db = MagicMock(spec=DatabaseServiceProtocol)
    mock_db.get_tables.return_value = [
        "config",
        "embedding_config",
        "system_prompts",
        "models",
        "doc_registry",
        "worker_state",
        "git_metadata",
        "git_selected_dirs",
        "sigma_spec",
        "doc_error",
    ]
    mock_db.get_table_count.return_value = 1
    mock_db.set_config.return_value = None

    # Should not raise with injected mock
    initialize_database(db_service=mock_db)

    # Verify mock was called
    mock_db.initialize.assert_called_once()
    mock_db.get_tables.assert_called_once()
    mock_db.set_config.assert_called_once_with("schema_version", 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
