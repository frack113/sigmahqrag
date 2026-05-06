"""Chat-related Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    mode: str = Field("search", description="Chat mode: search, explain, coverage")


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""

    response: str = Field(..., description="AI response text")
    timestamp: str = Field(..., description="ISO timestamp")
    citations: list[str] = Field(default_factory=list, description="Source citations")
    mode: str = Field("search", description="Mode used for response")


class ChatUploadResponse(BaseModel):
    """Response schema for YAML upload."""

    rule_name: str = Field(..., description="Name of the uploaded Sigma rule")
    rule_id: str = Field(..., description="ID of the uploaded Sigma rule")
    validated: bool = Field(True, description="Whether validation passed")


class ChatHistoryItem(BaseModel):
    """Chat history item."""

    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")
