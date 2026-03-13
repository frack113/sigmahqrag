"""
Custom exception hierarchy for SigmaHQ RAG application.

Provides a structured exception system for better error handling and debugging.
"""

from typing import Any


class SigmaHQError(Exception):
    """Base exception for SigmaHQ RAG application."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join([f"{k}={v}" for k, v in self.details.items()])
            return f"{self.message} (details: {details_str})"
        return self.message


class ConfigurationError(SigmaHQError):
    """Raised when configuration is invalid or missing."""
    pass


class ServiceError(SigmaHQError):
    """Raised when a service operation fails."""
    pass


class DatabaseError(ServiceError):
    """Raised when database operations fail."""
    pass


class RAGError(ServiceError):
    """Raised when RAG operations fail."""
    pass


class LLMError(ServiceError):
    """Raised when LLM operations fail."""
    pass


class ChatError(ServiceError):
    """Raised when chat operations fail."""
    pass


class ValidationError(SigmaHQError):
    """Raised when input validation fails."""
    pass


class CacheError(ServiceError):
    """Raised when cache operations fail."""
    pass


class NetworkError(ServiceError):
    """Raised when network operations fail."""
    pass


class FileError(ServiceError):
    """Raised when file operations fail."""
    pass


class AuthenticationError(SigmaHQError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(SigmaHQError):
    """Raised when authorization fails."""
    pass


class RateLimitError(ServiceError):
    """Raised when rate limits are exceeded."""
    pass


class EmbeddingError(ServiceError):
    """Raised when embedding operations fail."""
    pass
