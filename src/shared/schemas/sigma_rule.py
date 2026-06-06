"""Sigma rule schema — canonical model."""

import logging
from pathlib import Path
from typing import Any

import yaml

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SIGMA_REQUIRED_KEYS = {"logsource", "detection"}
_SIGMA_COMMON_KEYS = {"logsource", "detection", "condition", "title", "id"}

# Lenient heuristic for file-type detection: requires detection + at least
# one of title/id/condition.  Useful when ``logsource`` is absent but the
# file is still likely a Sigma rule rather than a plain YAML config.
_SIGMA_DETECTOR_KEYS = {"detection", "title", "condition", "id"}


class SigmaRule(BaseModel):
    """Sigma rule model — canonical source of truth.

    Used by both the legacy chunker (src/back/rag/chunker.py) and the
    document-level operations (src/back/documents/).
    """

    id: str
    title: str
    detection: dict[str, Any] = Field(default_factory=dict)
    condition: str = ""
    status: str | None = None
    level: str | None = None
    tags: list[str] = Field(default_factory=list)
    falsepositives: list[str] = Field(default_factory=list)
    description: str | None = None
    fields: list[str] = Field(default_factory=list)
    file_path: str | None = None
    line_number: int | None = None
    author: str | None = None
    date: str | None = None
    modified: str | None = None
    references: list[str] = Field(default_factory=list)
    logsource: dict[str, Any] = Field(default_factory=dict)
    license: str | None = None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        file_path: Path | None = None,
        line_number: int | None = None,
    ) -> "SigmaRule":
        """Create SigmaRule from dictionary."""
        rule_data = data.copy()
        if file_path:
            rule_data["file_path"] = str(file_path)
        if line_number is not None:
            rule_data["line_number"] = line_number
        return cls(**rule_data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)

    @property
    def path(self) -> Path | None:
        """Get file path as Path object."""
        return Path(self.file_path) if self.file_path else None


def is_sigma_rule_dict(data: dict[str, Any]) -> bool:
    """Fast check whether a parsed YAML dict looks like a Sigma rule.

    Primary heuristic (production default): requires both ``logsource`` and
    ``detection`` keys — these are mandatory in the Sigma spec and are the
    only keys checked in the reference ``SigmaRuleValidator``.

    An optional second heuristic (full heuristic) also requires *at least one*
    of ``condition``, ``title``, or ``id`` – this matches the old
    ``identify_file_type.py`` logic and is useful when ``logsource`` /
    ``detection`` appear in non-Sigma YAML files (e.g., CI configs).
    """
    if not isinstance(data, dict):
        return False

    has_mandatory = _SIGMA_REQUIRED_KEYS.issubset(data.keys())
    if not has_mandatory:
        return False

    # Production default — just require logsource + detection (Sigma spec).
    # To switch to the stricter heuristic uncomment:
    # return _SIGMA_COMMON_KEYS.issubset(data.keys())
    return True


def is_sigma_rule_candidate(data: dict[str, Any]) -> bool:
    """Lenient heuristic for file-type detection.

    Requires ``detection``, at least one of ``title``/``id``, and
    ``condition`` at the top level or nested inside ``detection``.
    Matches the original ``identify_file_type.py`` logic.
    """
    if not isinstance(data, dict):
        return False
    if "detection" not in data:
        return False
    if not any(k in data for k in ("title", "id")):
        return False
    cond = data.get("condition")
    if cond:
        return True
    detection = data.get("detection")
    return isinstance(detection, dict) and "condition" in detection


def is_sigma_rule_path(path: Path) -> bool:
    """Check whether *path* is a Sigma rule (loads YAML internally)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    return is_sigma_rule_dict(data)


def is_sigma_rule_content(content: str | bytes) -> bool:
    """Check whether the given text content is a Sigma rule.

    Accepts a raw YAML string or bytes.
    """
    if not content:
        return False
    try:
        data = yaml.safe_load(content)
    except (yaml.YAMLError, TypeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    return is_sigma_rule_dict(data)


def is_sigma_rule(
    data: dict[str, Any] | Path | str | bytes,
) -> bool:
    """Unified entry-point: detect whether *data* represents a Sigma rule.

    Dispatches to the appropriate specialised function based on input type:

    - ``dict``  → ``is_sigma_rule_dict``
    - ``Path``  → ``is_sigma_rule_path``
    - ``str`` / ``bytes`` → ``is_sigma_rule_content``
    """
    if isinstance(data, dict):
        return is_sigma_rule_dict(data)
    if isinstance(data, Path):
        return is_sigma_rule_path(data)
    if isinstance(data, (str, bytes)):
        return is_sigma_rule_content(data)
    return False
