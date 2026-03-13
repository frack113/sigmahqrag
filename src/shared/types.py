"""
Type definitions for SigmaHQ RAG application.

Provides type hints and data structures for better code documentation
and IDE support.
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Literal, TypedDict


# Chat-related types
class ChatMessage(TypedDict):
    """Type definition for chat messages."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    metadata: dict[str, Any] | None


class ChatCompletionRequest(TypedDict):
    """OpenAI-compatible chat completion request."""

    messages: list[ChatMessage]
    model: str
    temperature: float | None
    max_tokens: int | None
    max_completion_tokens: int | None
    top_p: float | None
    stream: bool | None
    stop: str | list[str] | None
    user: str | None
    metadata: dict[str, str] | None


# RAG-related types
class RAGResult(TypedDict):
    """Type definition for RAG results."""

    documents: list[str]
    metadata: list[dict[str, Any]]
    scores: list[float]


class RAGContext(TypedDict):
    """Type definition for RAG context."""

    query: str
    relevant_documents: list[str]
    metadata: list[dict[str, Any]]
    similarity_scores: list[float]


# Configuration dataclasses - used for type hints and serialization
@dataclass
class EmbeddingConfig:
    """Embedding configuration for RAG services."""

    model: str = "text-embedding-ada-002"
    base_url: str = "http://localhost:1234"
    api_key: str = "lm-studio"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def update(self, config: dict[str, Any]) -> None:
        """Update configuration from a dictionary.

        Args:
            config: Dictionary with configuration values to update
        """
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)


@dataclass
class LLMConfig:
    """LLM configuration for RAG services."""

    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int | None = None
    base_url: str = "http://localhost:1234"
    api_key: str = ""
    enable_streaming: bool = True


# Database types
class DatabaseConfig(TypedDict):
    """Type definition for database configuration."""

    path: str
    max_connections: int
    timeout: int


# Service status types
class ServiceStatus(TypedDict):
    """Type definition for service status."""

    name: str
    status: Literal["healthy", "unhealthy", "degraded"]
    uptime: float
    error_count: int
    last_error: str | None


class CacheStats(TypedDict):
    """Cache statistics."""

    total_entries: int
    valid_entries: int
    expired_entries: int
    cache_size_limit: int
    cache_ttl: int


# File processing types
class FileMetadata(TypedDict):
    """Type definition for file metadata."""

    filename: str
    file_size: int
    file_type: str
    created_date: datetime
    modified_date: datetime
    checksum: str


class ProcessingResult(TypedDict):
    """Processing results."""

    success: bool
    message: str
    processed_items: int
    errors: list[str]


# Configuration types
class AppConfig(TypedDict):
    """Application configuration structure."""

    llm: LLMConfig
    rag: EmbeddingConfig
    database: DatabaseConfig
    cache: dict[str, Any]
    logging: dict[str, Any]


# Async operation types
class AsyncOperation(TypedDict):
    """Type definition for async operations."""

    operation_id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: float
    result: Any | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None


# Performance metrics types
class PerformanceMetrics(TypedDict):
    """Performance metrics."""

    response_time: float
    throughput: float
    error_rate: float
    memory_usage: float
    cpu_usage: float
    cache_hit_rate: float


# Error handling types
class ErrorDetails(TypedDict):
    """Error details structure."""

    error_type: str
    error_message: str
    error_code: str | None
    timestamp: datetime
    context: dict[str, Any] | None


# Generic response types
class ApiResponse(TypedDict, total=False):
    """Type definition for API responses."""

    success: bool
    data: Any | None
    message: str | None
    error: ErrorDetails | None
    metadata: dict[str, Any] | None


class PaginatedResponse(TypedDict, total=False):
    """Paginated API responses."""

    items: list[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
    success: bool
    error: ErrorDetails | None


# Streaming types
class StreamingChunk(TypedDict):
    """Streaming response chunk."""

    chunk_id: str
    content: str
    timestamp: datetime
    is_final: bool


# Component types
class ComponentConfig(TypedDict):
    """Component configuration."""

    name: str
    enabled: bool
    config: dict[str, Any]
    dependencies: list[str]


# Event types
class EventData(TypedDict):
    """Event data structure."""

    event_type: str
    timestamp: datetime
    source: str
    data: dict[str, Any]


# Validation types
class ValidationResult(TypedDict):
    """Validation results."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metadata: dict[str, Any] | None


# Utility types
class ProgressCallback:
    """Type definition for progress callback functions."""

    def __call__(self, progress: float, message: str) -> None:
        pass


class AsyncGeneratorFunction:
    """Type definition for async generator functions."""

    def __call__(self, *args, **kwargs) -> AsyncGenerator[Any, None]:
        pass


# Dataclass-based types for more complex structures
@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""

    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None
    chunk_id: str | None = None


@dataclass
class SearchResult:
    """Search result structure."""

    document_id: str
    content: str
    metadata: dict[str, Any]
    similarity_score: float
    rank: int


@dataclass
class ConversationContext:
    """Conversation context structure."""

    history: list[ChatMessage]
    current_topic: str | None
    user_preferences: dict[str, Any]
    session_id: str
    created_at: datetime
