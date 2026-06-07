"""Model management types."""

from __future__ import annotations


class HFRepo:
    """HuggingFace repository identifier."""

    VALID_REPO_TYPES = {"models", "datasets", "spaces"}

    def __init__(self, owner: str, name: str, repo_type: str = "models") -> None:
        if repo_type not in self.VALID_REPO_TYPES:
            raise ValueError(
                f"Invalid repo_type: {repo_type}. Must be one of {self.VALID_REPO_TYPES}"
            )
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

        Raises:
            ValueError: If repo_id is not in owner/name format
        """
        parts = repo_id.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid repo_id format: '{repo_id}'. Expected 'owner/name'.")
        return cls(owner=parts[0], name=parts[1])

    def __repr__(self) -> str:
        return f"HFRepo({self.owner}/{self.name})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HFRepo):
            return False
        return self.full_id == other.full_id

    def __hash__(self) -> int:
        return hash(self.full_id)
