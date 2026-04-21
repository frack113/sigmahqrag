"""Sigma rule data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SigmaRule:
    """Sigma rule data model."""

    id: str
    title: str
    detection: dict[str, Any]
    status: str = "stable"
    level: str = "medium"
    file_path: Path | None = None
    line_number: int | None = None
    fields: list[str] = field(default_factory=list)
    falsepositives: list[str] = field(default_factory=list)
    description: str | None = None
    author: str | None = None
    date: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], file_path: Path | None = None, line_number: int | None = None) -> SigmaRule:
        """Create SigmaRule from dictionary."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            detection=data.get("detection", {}),
            status=data.get("status", "stable"),
            level=data.get("level", "medium"),
            file_path=file_path,
            line_number=line_number,
            fields=data.get("fields", []),
            falsepositives=data.get("falsepositives", []),
            description=data.get("description"),
            author=data.get("author"),
            date=data.get("date"),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "detection": self.detection,
            "status": self.status,
            "level": self.level,
        }
        if self.fields:
            result["fields"] = self.fields
        if self.falsepositives:
            result["falsepositives"] = self.falsepositives
        if self.description:
            result["description"] = self.description
        if self.author:
            result["author"] = self.author
        if self.date:
            result["date"] = self.date
        if self.tags:
            result["tags"] = self.tags
        return result
