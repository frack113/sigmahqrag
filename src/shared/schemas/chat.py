"""Chat-related Pydantic schemas."""

from __future__ import annotations

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
    citations: list[str] = Field(default_factory=list, description="Source citations")
    mode: str = Field("search", description="Mode used for response")
