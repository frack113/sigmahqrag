"""Sigma rule schema — canonical model."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


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
