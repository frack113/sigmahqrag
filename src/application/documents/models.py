"""Document models and schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request to ingest Sigma rules."""

    directory: str | None = None
    recursive: bool = True
    mode: str = "flat"
    selected_dirs: list[str] = Field(default_factory=list)


class IngestResult(BaseModel):
    """Result for a single file."""

    file: str
    success: bool
    rule_id: str | None = None
    error: str | None = None
    chunks: int = 0
