import logging
import re
import sys

from src.config.constants import SCHEMA_VERSION


class _Filter2xx(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname != "INFO":
            return True
        msg = record.getMessage()
        # Uvicorn access log format: '127.0.0.1 - "GET /path HTTP/1.1" 200 OK'
        return not bool(re.search(r'"\s+2\d{2}\s+\d{3}', msg))


def _validate_schema_version() -> None:
    """Validate project is initialized by checking schema_version in DuckDB."""
    try:
        from src.infrastructure.database import DatabaseService

        db = DatabaseService()
        db.initialize()
        schema_version = db.get_config("schema_version")
        db.close()

        if schema_version is None:
            print(
                "✗ Project not initialized (schema_version not found). Run 'uv run python init_projet.py' first.",
                file=sys.stderr,
            )
            sys.exit(1)

        if schema_version != SCHEMA_VERSION:
            print(
                f"✗ Schema version mismatch: expected {SCHEMA_VERSION}, got {schema_version}. "
                "Run 'uv run python init_projet.py' to reinitialize.",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"✓ Schema version {schema_version} validated")
    except Exception as e:
        print(f"✗ Failed to validate schema version: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    import copy
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    # Check schema version in DuckDB
    _validate_schema_version()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    log_config = copy.deepcopy(LOGGING_CONFIG)
    log_config["filters"] = {
        "filter2xx": {"()": _Filter2xx},
    }
    log_config["handlers"]["access"]["filters"] = ["filter2xx"]

    uvicorn.run(
        "src.main:create_app",
        host="0.0.0.0",
        port=7860,
        factory=True,
        log_config=log_config,
        timeout_graceful_shutdown=5,
    )
