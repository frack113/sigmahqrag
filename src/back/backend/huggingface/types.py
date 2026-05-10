"""Types for HuggingFace models."""

from __future__ import annotations


class HFRepo:
    """HuggingFace repository identifier."""

    def __init__(self, owner: str, name: str, repo_type: str = "models") -> None:
        """Initialize HFRepo.

        Args:
            owner: Repository owner/organization
            name: Repository name
            repo_type: Repository type (models, datasets, spaces)
        """
        self.owner = owner
        self.name = name
        self.repo_type = repo_type

    @property
    def full_id(self) -> str:
        """Full repository ID."""
        return f"{self.owner}/{self.name}"

    @classmethod
    def from_string(cls, repo_id: str) -> HFRepo:
        """Create HFRepo from string.

        Args:
            repo_id: Repository ID in owner/name format

        Returns:
            HFRepo instance
        """
        parts = repo_id.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid repo_id: {repo_id}")
        return cls(owner=parts[0], name=parts[1])

    @classmethod
    def from_id(cls, repo_id: str) -> HFRepo:
        """Create HFRepo from full repository ID.

        Args:
            repo_id: Full repository ID

        Returns:
            HFRepo instance
        """
        return cls.from_string(repo_id)

    def __repr__(self) -> str:
        return f"HFRepo({self.owner}/{self.name})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HFRepo):
            return False
        return self.full_id == other.full_id
