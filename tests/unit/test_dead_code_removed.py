"""Verify all dead references have been cleaned up."""

from __future__ import annotations

from pathlib import Path


def test_no_setup_py_in_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "setup.py" not in readme


def test_no_sigmarag_toml_in_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "sigmarag.toml" not in readme


def test_no_sigmarag_toml_in_gitignore() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "sigmarag.toml" not in gitignore


def test_no_setup_py_in_schema_validation() -> None:
    content = Path("src/core/schema_validation.py").read_text(encoding="utf-8")
    assert "setup.py" not in content


def test_old_e2e_test_deleted() -> None:
    assert not Path("tests/integration/scripts/test_init_projet_e2e.py").exists()


def test_old_toml_service_deleted() -> None:
    assert not Path("src/shared/toml_service.py").exists()


def test_old_toml_test_deleted() -> None:
    assert not Path("tests/unit/shared/test_toml_service.py").exists()


def test_shared_init_no_toml_import() -> None:
    content = Path("src/shared/__init__.py").read_text(encoding="utf-8")
    assert "TOMLService" not in content
    assert "deep_merge" not in content


def test_constants_no_toml_keys() -> None:
    content = Path("src/config/constants.py").read_text(encoding="utf-8")
    assert "TOML_SECTIONS" not in content
    assert "TOML_CONFIG_KEYS" not in content


def test_no_duplicate_handlers_in_client() -> None:
    content = Path("src/infrastructure/llm/llamacpp/client.py").read_text(encoding="utf-8")
    # Count occurrences of the duplicate pattern
    count = content.count("Failed to erase llama.cpp slot cache")
    assert count == 1, f"Expected 1, found {count} occurrences of duplicate handler"
