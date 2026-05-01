"""
Tests to validate exact version pinning in pyproject.toml.
All dependencies MUST use == not >= for Air-Gap reproducibility.
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
    """Validate that all dependencies use exact version pinning (==)."""

    def test_no_greater_equal_in_dependencies(self, pyproject_content: str):
        """RED phase: Test that no dependency uses >= in version specifier."""
        # Extract dependencies section
        in_deps = False
        deps_failures = []

        for line in pyproject_content.splitlines():
            line = line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if line.startswith("]"):
                    break
                # Check each dependency line
                if line and not line.startswith("#"):
                    # Remove quotes and whitespace
                    dep = line.strip('", \n')
                    if dep:
                        # Check for >= (should not exist)
                        if ">=" in dep:
                            deps_failures.append(dep)

        assert len(deps_failures) == 0, (
            f"Dependencies using >= found (must use == for Air-Gap reproducibility):\n"
            f"{chr(10).join(f'  - {d}' for d in deps_failures)}\n"
            "Fix by changing >= to =="
        )

    def test_all_dependencies_use_exact_pinned_versions(self, pyproject_content: str):
        """GREEN phase: Validate all dependencies use ==."""
        in_deps = False
        deps_without_exact = []

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
                        # Must use == for exact pinning
                        if "==" not in dep:
                            deps_without_exact.append(dep)

        assert len(deps_without_exact) == 0, (
            f"Dependencies without exact == pinning found:\n"
            f"{chr(10).join(f'  - {d}' for d in deps_without_exact)}\n"
            "Fix by adding == with exact version"
        )

    def test_specific_critical_packages_pinned(self, pyproject_content: str):
        """Validate critical packages are pinned with ==."""
        critical_packages = {
            "fastapi": "0.136.1",
            "llama-index": "0.14.21",
            "llama-index-vector-stores-qdrant": None,  # Version checked but flexible
            "llama-index-llms-llamafile": None,
            "llama-index-embeddings-huggingface": None,
        }

        in_deps = False
        deps_dict = {}

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
                        # Parse package name and version
                        match = re.match(r'([^=<>!]+)(==|>=|<=|~=|!=)(.+)', dep)
                        if match:
                            pkg_name = match.group(1).strip()
                            operator = match.group(2)
                            version = match.group(3).strip()
                            deps_dict[pkg_name] = (operator, version)

        # Check that critical packages use ==
        for pkg, expected_ver in critical_packages.items():
            assert pkg in deps_dict, f"Critical package '{pkg}' not found in dependencies"
            operator, version = deps_dict[pkg]
            assert operator == "==", (
                f"Package '{pkg}' uses '{operator}' but must use '==' for Air-Gap reproducibility"
            )
            if expected_ver:
                assert version == expected_ver, (
                    f"Package '{pkg}' version mismatch: expected '{expected_ver}', got '{version}'"
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
