"""Schema version validation for the project."""

import sys

from src.config.constants import SCHEMA_VERSION
from src.infrastructure.database import DatabaseService


def validate_schema_version() -> None:
    """Validate project is initialized by checking schema_version in DuckDB."""
    try:
        db = DatabaseService()
        db.initialize()
        schema_version = db.get_config("schema_version")

        if schema_version is None:
            print(
                "\u2717 Project not initialized (schema_version not found). "
                "Run the application with `uv run python main.py` to initialize.",
                file=sys.stderr,
            )
            sys.exit(1)

        if schema_version != SCHEMA_VERSION:
            print(
                "\u2717 Schema version mismatch: Use the Config tab to fix the database.",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"\u2713 Schema version {schema_version} validated")
        db.close()
    except Exception as e:
        print(f"\u2717 Failed to validate schema version: {e}", file=sys.stderr)
        sys.exit(1)
