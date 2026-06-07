"""Chat, search and mode Pydantic schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    mode: str = Field("search", description="Chat mode: search, explain, coverage")
    model: str = Field("", description="Selected LLM model (repo_id/filename)")
    prompt_id: str = Field("", description="Selected system prompt ID")


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""

    response: str = Field(..., description="AI response text")
    timestamp: str = Field(..., description="ISO timestamp")
    citations: list[dict[str, Any]] = Field(default_factory=list, description="Source citations")
    mode: str = Field("search", description="Mode used for response")


class ChatMode(StrEnum):
    """Chat operation modes."""

    SEARCH = "search"
    EXPLAIN = "explain"
    COVERAGE = "coverage"

    @classmethod
    def values(cls) -> list[str]:
        """Get all mode values."""
        return [m.value for m in cls]


class SearchRequest(BaseModel):
    """Search request."""

    query: str
    limit: int = Field(default=10, ge=1, le=100)
    mode: str = Field(default="search")


class SearchResponse(BaseModel):
    """Search response."""

    data: list[dict[str, Any]]
    meta: dict[str, Any] = Field(default_factory=dict)
