"""Document models and schemas."""

from __future__ import annotations

import warnings

from pydantic import BaseModel, Field

from src.shared.schemas.sigma_rule import SigmaRule as _SigmaRule

warnings.warn(
    "Import SigmaRule from src.back.documents.models is deprecated; "
    "use src.shared.schemas.sigma_rule.SigmaRule instead.",
    DeprecationWarning,
    stacklevel=2,
)

SigmaRule = _SigmaRule


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
    mode: str = "flat"


class IngestResult(BaseModel):
    """Result for a single file."""

    file: str
    success: bool
    rule_id: str | None = None
    error: str | None = None
    chunks: int = 0
