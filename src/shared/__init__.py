"""
SigmaHQ RAG - Shared modules and utilities.

This module provides shared functionality used across the application.
"""

from .base_service import BaseService, CacheService

# Configuration manager
from .config_manager import ConfigManager
from .constants import (
    # Application constants - only identity and infrastructure
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    AUTHOR,
    LICENSE_,
    # Database constants
    DEFAULT_DB_MAX_CONNECTIONS,
    DEFAULT_DB_PATH,
    DEFAULT_DB_TIMEOUT,
    # Environment variable keys (values come from config.json)
    ENV_LLM_MODEL,
    ENV_LLM_BASE_URL,
    ENV_LLM_TEMPERATURE,
    ENV_LLM_MAX_TOKENS,
    # Service identifiers
    SERVICE_CHAT,
    SERVICE_CONFIG,
    SERVICE_DATA,
    SERVICE_DATABASE,
    SERVICE_EMBEDDING,
    SERVICE_FILE_PROCESSOR,
    SERVICE_GITHUB,
    SERVICE_LLM,
    SERVICE_RAG,
    # Status codes (only status values)
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    STATUS_DEGRADED,
)
from .exceptions import (
    BaseServiceError,
    BaseServiceNotInitializedError,
    ChatError,
    ConfigurationError,
    DatabaseError,
    DataError,
    FileError,
    LLMError,
    NetworkError,
    RAGError,
    RepoServiceError,
    ServiceError,
    ValidationError,
)
from .stats_manager import (
    ServiceStats,
    get_system_metrics,
)

# Import the repository error from models
from .types import (
    ApiResponse,
    AppConfig,
    AsyncOperation,
    CacheStats,
    ChatMessage,
    ComponentConfig,
    ConversationContext,
    DatabaseConfig,
    DocumentChunk,
    EmbeddingConfig,
    ErrorDetails,
    EventData,
    FileMetadata,
    LLMConfig,
    PaginatedResponse,
    PerformanceMetrics,
    ProcessingResult,
    SearchResult,
    ServiceStatus,
    StreamingChunk,
    ValidationResult,
)
from .utils import (
    chunk_text,
    cleanup_temp_files,
    create_directory_if_not_exists,
    deep_merge,
    format_size,
    generate_hash,
    get_app_directory,
    get_cpu_usage,
    get_file_extension,
    get_file_info,
    get_memory_usage,
    handle_service_errors,
    is_file_extension_allowed,
    parse_iso_timestamp,
    retry_with_backoff,
    safe_json_dumps,
    safe_json_loads,
    sanitize_filename,
    validate_file_upload,
)

__all__ = [
    # Application constants (identity only)
    "APP_NAME",
    "APP_VERSION",
    "APP_DESCRIPTION",
    "AUTHOR",
    "LICENSE_",
    # Database constants
    "DEFAULT_DB_MAX_CONNECTIONS",
    "DEFAULT_DB_PATH",
    "DEFAULT_DB_TIMEOUT",
    # Environment variable keys
    "ENV_LLM_MODEL",
    "ENV_LLM_BASE_URL",
    "ENV_LLM_TEMPERATURE",
    "ENV_LLM_MAX_TOKENS",
    # Service identifiers
    "SERVICE_CHAT",
    "SERVICE_CONFIG",
    "SERVICE_DATA",
    "SERVICE_DATABASE",
    "SERVICE_EMBEDDING",
    "SERVICE_FILE_PROCESSOR",
    "SERVICE_GITHUB",
    "SERVICE_LLM",
    "SERVICE_RAG",
    # Status codes
    "STATUS_HEALTHY",
    "STATUS_UNHEALTHY",
    "STATUS_DEGRADED",
    # Exceptions
    "BaseServiceError",
    "BaseServiceNotInitializedError",
    "ConfigurationError",
    "DatabaseError",
    "DataError",
    "FileError",
    "LLMError",
    "RepoServiceError",
    "EmbeddingError",
    "NetworkError",
    "RAGError",
    "ChatError",
    "ServiceError",
    "ValidationError",
    # Type definitions
    "ChatMessage",
    "ValidationResult",
    "LLMConfig",
    "EmbeddingConfig",
    "DatabaseConfig",
    "ServiceStatus",
    "CacheStats",
    "FileMetadata",
    "ProcessingResult",
    "AppConfig",
    "AsyncOperation",
    "PerformanceMetrics",
    "ErrorDetails",
    "ApiResponse",
    "PaginatedResponse",
    "StreamingChunk",
    "ComponentConfig",
    "EventData",
    "DocumentChunk",
    "SearchResult",
    "ConversationContext",
    # Utilities
    "handle_service_errors",
    "retry_with_backoff",
    "chunk_text",
    "format_size",
    "get_file_info",
    "validate_file_upload",
    "sanitize_filename",
    "get_file_extension",
    "is_file_extension_allowed",
    "generate_hash",
    "cleanup_temp_files",
    "parse_iso_timestamp",
    "get_app_directory",
    "create_directory_if_not_exists",
    "safe_json_loads",
    "safe_json_dumps",
    "deep_merge",
    "get_cpu_usage",
    "get_memory_usage",
    # Stats & Caching
    "ServiceStats",
    "get_system_metrics",
    # Base classes
    "BaseService",
    "CacheService",
    # Configuration (MUST have config.json)
    "ConfigManager",
]
