"""Frontend assets package."""

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"

TEMPLATES_DIR = str(_TEMPLATES_DIR)
STATIC_DIR = str(_STATIC_DIR)
