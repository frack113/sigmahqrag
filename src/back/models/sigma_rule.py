"""Sigma rule domain model."""

from dataclasses import dataclass


@dataclass
class SigmaRuleModel:
    """Sigma rule domain model."""

    id: str
    title: str
    detection: dict
    status: str | None = None
    level: str | None = None
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        """Post-initialization."""
        if self.tags is None:
            self.tags = []
