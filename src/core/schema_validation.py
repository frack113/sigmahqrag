"""Schema version validation for the project."""

import sys

from src.config.constants import SCHEMA_VERSION
from src.infrastructure.database import DatabaseService


def validate_schema_version() -> None:
    """Validate project is initialized by checking schema_version in DuckDB.

    Raises SystemExit on validation failure.
    """
    try:
        db = DatabaseService()
        db.initialize()
        schema_version: str | None = db.get_config("schema_version")
        db.close()

        if schema_version is None:
            print(
                "\u2717 Project not initialized (schema_version not found). "
                "Run 'uv run python setup.py' first.",
                file=sys.stderr,
            )
            sys.exit(1)

        if schema_version != SCHEMA_VERSION:
            print(
                f"\u2717 Schema version mismatch: expected {SCHEMA_VERSION}, got {schema_version}. "
                "Run 'uv run python setup.py' to reinitialize.",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"\u2713 Schema version {schema_version} validated")
    except Exception as e:
        print(f"\u2717 Failed to validate schema version: {e}", file=sys.stderr)
        sys.exit(1)
