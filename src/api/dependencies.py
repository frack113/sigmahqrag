"""FastAPI dependencies."""

from functools import lru_cache


@lru_cache
def get_settings() -> dict:
    """Get application settings."""
    return {
        "app_name": "SigmaHQ RAG",
        "version": "0.1.0",
    }
