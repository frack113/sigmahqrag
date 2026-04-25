"""Document models and schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SigmaRule(BaseModel):
    """Sigma rule schema."""

    id: str
    title: str
    detection: dict[str, Any]
    condition: str
    description: str | None = None
    author: str | None = None
    date: str | None = None
    modified: str | None = None
    references: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    level: str | None = None
    falsepositives: list[str] = Field(default_factory=list)
    logsource: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None
    license: str | None = None


class ValidationError(BaseModel):
    """Validation error for a single field."""

    field: str
    message: str


class ValidationResult(BaseModel):
    """Result of validating a Sigma rule."""

    valid: bool
    rule: SigmaRule | None = None
    errors: list[ValidationError] = Field(default_factory=list)
    file_path: str | None = None


class IngestRequest(BaseModel):
    """Request to ingest Sigma rules."""

    directory: str | None = None
    recursive: bool = True


class IngestResponse(BaseModel):
    """Response from ingesting Sigma rules."""

    total_files: int
    successful: int
    failed: int
    results: list[IngestResult]


class IngestResult(BaseModel):
    """Result for a single file."""

    file: str
    success: bool
    rule_id: str | None = None
    error: str | None = None
