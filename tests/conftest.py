"""Global test configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add project root to sys.path for all tests
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset module state between tests."""
    # Clear any cached singletons
    import src.back.database.core as db_core

    db_core.DatabaseServiceCore._instance = None
    yield
    db_core.DatabaseServiceCore._instance = None
