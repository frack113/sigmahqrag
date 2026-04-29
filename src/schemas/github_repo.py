"""GitHub repository schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GitHubRepoMetadata(BaseModel):
    """Metadata for a GitHub repository."""

    org: str = Field(..., description="GitHub organization or username")
    name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Default branch to track")
    extensions_to_index: list[str] = Field(
        default_factory=lambda: ["*.yml", "*.yaml"],
        description="File extensions to index in Qdrant",
    )


class GitHubRepoCreate(BaseModel):
    """Request to clone a new GitHub repository."""

    org: str = Field(..., description="GitHub organization or username")
    name: str = Field(..., description="Repository name")
    branch: str = Field(default="main", description="Branch to clone")
    url: str = Field(..., description="Git repository URL")
    extensions_to_index: list[str] = Field(
        default_factory=lambda: ["*.yml", "*.yaml"],
        description="File extensions to index in Qdrant",
    )


class GitHubRepoResponse(BaseModel):
    """Response for GitHub repository operations."""

    success: bool
    message: str | None = None
    repo: dict[str, Any] | None = None
    error: str | None = None


class GitHubRepoInfo(BaseModel):
    """Repository info with metadata."""

    name: str
    path: str
    metadata: GitHubRepoMetadata | None = None
