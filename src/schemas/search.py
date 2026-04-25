"""Search request/response schema."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request."""

    query: str
    limit: int = Field(default=10, ge=1, le=100)
    mode: str = Field(default="search")


class SearchResponse(BaseModel):
    """Search response."""

    data: list[dict]
    meta: dict = Field(default_factory=dict)
