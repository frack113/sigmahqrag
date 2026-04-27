from __future__ import annotations

from pydantic import BaseModel, Field, validator


class HFRepo(BaseModel):
    """Represents a HuggingFace repository."""

    owner: str
    name: str

    @property
    def full_id(self) -> str:
        """Returns the full repository ID (owner/name)."""
        return f"{self.owner}/{self.name}"

    @classmethod
    def from_string(cls, identifier: str) -> HFRepo:
        """Create an HFRepo from a string like 'owner/name'."""
        if "/" not in identifier:
            raise ValueError(f"Invalid HF repository identifier: {identifier}. Expected 'owner/name'")
        
        owner, name = identifier.split("/", 1)
        return cls(owner=owner, name=name)

    def to_string(self) -> str:
        """Convert the HFRepo to its string representation."""
        return self.full_id

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"HFRepo(owner='{self.owner}', name='{self.name}')"
