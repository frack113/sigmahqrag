from datetime import datetime, timezone

from src.shared.utils.identify_file_type import FileType, identify


def iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["FileType", "identify", "iso_now"]
