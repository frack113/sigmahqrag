"""Sigma rule domain model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SigmaRuleModel:
    """Sigma rule domain model."""

    id: str
    title: str
    detection: dict
    status: Optional[str] = None
    level: Optional[str] = None
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        """Post-initialization."""
        if self.tags is None:
            self.tags = []