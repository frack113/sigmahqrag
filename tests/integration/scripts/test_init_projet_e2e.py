"""End-to-end integration test for setup.py full initialization."""

import subprocess
import tempfile
import shutil
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


@pytest.mark.skip(
    reason="setup.py no longer exists in the project — setup is handled through main.py / Config"
)
def test_full_init_e2e_creates_all_structure(temp_project_dir):
    """Test that running setup.py creates all required structure."""
    project_root = Path(__file__).parent.parent.parent.parent

    # Copy required files to temp dir
    shutil.copy(project_root / "setup.py", temp_project_dir / "setup.py")
    shutil.copytree(project_root / "src", temp_project_dir / "src")
    shutil.copytree(project_root / "templates", temp_project_dir / "templates")
    shutil.copy(project_root / "pyproject.toml", temp_project_dir / "pyproject.toml")

    # Run in non-interactive mode
    result = subprocess.run(
        [sys.executable, "setup.py", "--defaults"],
        cwd=temp_project_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, f"setup.py failed: {result.stderr}"

    # Verify all data directories created
    data_dirs = [
        "data",
        "data/bin",
        "data/models",
        "data/models/llm",
        "data/models/embeddings",
        "data/duckdb",
        "data/logs",
        "data/pids",
        "data/qdrant_storage",
        "data/temp",
        "data/documents",
        "data/documents/local",
        "data/documents/sigmaref",
        "data/github",
        "data/rag_cache",
    ]

    for d in data_dirs:
        assert (temp_project_dir / d).exists(), f"Directory {d} not created"
        assert (temp_project_dir / d).is_dir()

    # Verify config file created
    assert (temp_project_dir / "sigmarag.toml").exists()
    config_content = (temp_project_dir / "sigmarag.toml").read_text()
    assert "[services.llama]" in config_content
    assert "[services.qdrant]" in config_content
    assert "[logging]" in config_content
    assert "[Hardware]" in config_content
    assert "[backend]" not in config_content

    # Verify sigma-specification cloned
    assert (
        temp_project_dir / "data" / "specification" / "sigmahq" / "sigma-specification"
    ).exists()
    assert (
        temp_project_dir / "data" / "specification" / "sigmahq" / "sigma-specification" / ".git"
    ).exists()

    # Verify DuckDB initialized with schema_version
    from src.infrastructure.database import DatabaseService

    db = DatabaseService()
    db.initialize()
    schema_version = db.get_config("schema_version")
    db.close()
    assert schema_version == 1, f"Expected schema_version=1, got {schema_version}"

    # Verify tables exist
    expected_tables = {
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
        "release_cache",
    }
    db = DatabaseService()
    db.initialize()
    tables = set(db.get_tables())
    db.close()
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"


@pytest.mark.skip(
    reason="setup.py no longer exists in the project — setup is handled through main.py / Config"
)
def test_init_idempotent_second_run(temp_project_dir):
    """Test that running setup.py twice works (idempotent)."""
    project_root = Path(__file__).parent.parent.parent.parent

    # Copy required files
    shutil.copy(project_root / "setup.py", temp_project_dir / "setup.py")
    shutil.copytree(project_root / "src", temp_project_dir / "src")
    shutil.copytree(project_root / "templates", temp_project_dir / "templates")
    shutil.copy(project_root / "pyproject.toml", temp_project_dir / "pyproject.toml")

    # First run
    result1 = subprocess.run(
        [sys.executable, "setup.py", "--defaults"],
        cwd=temp_project_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result1.returncode == 0, f"First run failed: {result1.stderr}"

    # Second run (should succeed: dirs/config already exist)
    result2 = subprocess.run(
        [sys.executable, "setup.py", "--defaults"],
        cwd=temp_project_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result2.returncode == 0, f"Second run failed: {result2.stderr}"

    # Verify structure still intact
    assert (temp_project_dir / "sigmarag.toml").exists()
    assert (
        temp_project_dir / "data" / "specification" / "sigmahq" / "sigma-specification"
    ).exists()

    from src.infrastructure.database import DatabaseService

    db = DatabaseService()
    db.initialize()
    schema_version = db.get_config("schema_version")
    db.close()
    assert schema_version == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
