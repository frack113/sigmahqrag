"""
Tests to validate version pinning in pyproject.toml.
Dependencies use >= for flexibility; uv.lock provides exact pinning for Air-Gap reproducibility.
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def pyproject_path() -> Path:
    return Path("pyproject.toml")


@pytest.fixture
def pyproject_content(pyproject_path: Path) -> str:
    return pyproject_path.read_text(encoding="utf-8")


class TestVersionPinning:
    """Validate dependency versioning strategy."""

    def test_all_dependencies_have_version_specifiers(self, pyproject_content: str):
        """Validate all dependencies specify a version."""
        in_deps = False
        deps_without_version = []

        for line in pyproject_content.splitlines():
            line = line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if line.startswith("]"):
                    break
                if line and not line.startswith("#"):
                    dep = line.strip('", \n')
                    if dep:
                        if not re.search(r"[=<>!~]", dep):
                            deps_without_version.append(dep)

        assert len(deps_without_version) == 0, (
            f"Dependencies without version specifiers found:\n"
            f"{chr(10).join(f'  - {d}' for d in deps_without_version)}\n"
        )

    def test_uv_lock_exists(self):
        """Validate uv.lock exists (provides exact pinning for Air-Gap)."""
        lock_path = Path("uv.lock")
        assert lock_path.exists(), (
            "uv.lock must exist for Air-Gap reproducibility!\n"
            "Run 'uv lock' to generate it."
        )

    def test_uv_lock_not_in_gitignore(self):
        """Validate that uv.lock is NOT in .gitignore."""
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            pytest.skip(".gitignore not found")

        content = gitignore_path.read_text(encoding="utf-8")
        assert "uv.lock" not in content, (
            "uv.lock must NOT be in .gitignore for Air-Gap reproducibility!\n"
            "The lock file must be committed to version control."
        )
