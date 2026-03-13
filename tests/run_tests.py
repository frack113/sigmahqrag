#!/usr/bin/env python3
"""
Test runner script for SigmaHQ RAG application.

This script runs tests without requiring external dependencies like LM Studio
or ChromaDB, making it suitable for CI/CD environments.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run the test suite with proper configuration."""

    # Set environment variables for testing
    os.environ.update(
        {
            "LM_STUDIO_BASE_URL": "http://test:1234",
            "LM_STUDIO_API_KEY": "test-key",
            "CHROMADB_PATH": "./test_data/chromadb",
            "TEST_MODE": "true",
        }
    )

    # Test command with proper configuration
    test_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",  # Verbose output
        "--cov=src",  # Coverage for src directory
        "--cov-report=xml",  # XML coverage report for Codecov
        "--cov-report=term",  # Terminal coverage report
        "-m",
        "not slow",  # Skip slow tests
        "--tb=short",  # Short traceback format
        "--no-header",  # Clean output
    ]

    print("🧪 Running SigmaHQ RAG Application Tests")
    print("=" * 50)
    print("Test Configuration:")
    print("- Mock external dependencies (LM Studio, ChromaDB)")
    print("- Unit tests only (no slow integration tests)")
    print("- Coverage reporting enabled")
    print("- Verbose output")
    print("=" * 50)

    try:
        # Run the tests
        result = subprocess.run(test_cmd, cwd=Path(__file__).parent.parent)

        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("📊 Test coverage report generated")
            return True
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            return False

    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
