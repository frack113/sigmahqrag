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
