"""Sigma rule schema."""

from pydantic import BaseModel, Field


class SigmaRule(BaseModel):
    """Sigma rule model."""

    id: str
    title: str
    detection: dict = Field(default_factory=dict)
    status: str | None = None
    level: str | None = None
    tags: list[str] = Field(default_factory=list)
    falsepositives: list[str] = Field(default_factory=list)
    file_path: str | None = None
    line_number: int | None = None
    description: str | None = None
    fields: list[str] = Field(default_factory=list)
