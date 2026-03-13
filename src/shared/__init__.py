"""
SigmaHQ RAG - Shared modules and utilities.

This module provides shared functionality used across the application.
"""

from .base_service import BaseService, CacheService

# Configuration manager
from .config_manager import (
    ConfigManager,
    create_config_manager,
)
from .constants import (
    # Application constants
    APP_NAME,
    APP_VERSION,
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CACHE_ENABLED,
    # Cache configuration defaults
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CONVERSATION_HISTORY_LIMIT,
    DEFAULT_DB_MAX_CONNECTIONS,
    # Database configuration defaults
    DEFAULT_DB_PATH,
    DEFAULT_DB_TIMEOUT,
    # RAG configuration defaults
    DEFAULT_EMBEDDING_MODEL,
    # GitHub configuration defaults
    DEFAULT_GITHUB_API_BASE_URL,
    DEFAULT_GITHUB_RATE_LIMIT_DELAY,
    DEFAULT_LLM_API_KEY,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_ENABLE_STREAMING,
    DEFAULT_LLM_MAX_TOKENS,
    # LLM configuration defaults
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TEMPERATURE,
    # LM Studio configuration defaults
    DEFAULT_LM_STUDIO_BASE_URL,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_FORMAT,
    # Logging configuration defaults
    DEFAULT_LOG_LEVEL,
    # File processing configuration defaults
    DEFAULT_MAX_FILE_SIZE_MB,
    # Performance configuration defaults
    DEFAULT_MAX_WORKERS,
    DEFAULT_RAG_MIN_SCORE,
    DEFAULT_RAG_N_RESULTS,
    DEFAULT_RAG_PERSIST_DIRECTORY,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TEMP_DIR,
    DEFAULT_UPLOAD_DIR,
    SERVICE_APPLICATION,
    # Service constants
    SERVICE_CHAT,
    SERVICE_CONFIG,
    SERVICE_DATA,
    SERVICE_DATABASE,
    SERVICE_EMBEDDING,
    SERVICE_FILE_PROCESSOR,
    SERVICE_GITHUB,
    SERVICE_LLM,
    SERVICE_LM_STUDIO,
    SERVICE_RAG,
    STATUS_DEGRADED,
    # Status codes
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
)
from .exceptions import (
    BaseServiceError,
    BaseServiceNotInitializedError,
    ChatError,
    ConfigurationError,
    DatabaseError,
    DataError,
    EmbeddingError,
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
    # Application constants
    "APP_NAME",
    "APP_VERSION",
    # LLM configuration defaults
    "DEFAULT_LLM_MODEL",
    "DEFAULT_LLM_BASE_URL",
    "DEFAULT_LLM_API_KEY",
    "DEFAULT_LLM_TEMPERATURE",
    "DEFAULT_LLM_MAX_TOKENS",
    "DEFAULT_LLM_ENABLE_STREAMING",
    # RAG configuration defaults
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_RAG_N_RESULTS",
    "DEFAULT_RAG_MIN_SCORE",
    # Database configuration defaults
    "DEFAULT_DB_PATH",
    "DEFAULT_DB_MAX_CONNECTIONS",
    "DEFAULT_DB_TIMEOUT",
    # Service constants
    "SERVICE_CHAT",
    "SERVICE_LLM",
    "SERVICE_RAG",
    "SERVICE_CONFIG",
    "SERVICE_FILE_PROCESSOR",
    "SERVICE_DATA",
    "SERVICE_DATABASE",
    "SERVICE_GITHUB",
    "SERVICE_LM_STUDIO",
    "SERVICE_EMBEDDING",
    "SERVICE_APPLICATION",
    "DEFAULT_CONVERSATION_HISTORY_LIMIT",
    # Cache configuration defaults
    "DEFAULT_CACHE_SIZE",
    "DEFAULT_CACHE_TTL",
    "DEFAULT_CACHE_ENABLED",
    # File processing configuration defaults
    "DEFAULT_MAX_FILE_SIZE_MB",
    "DEFAULT_ALLOWED_FILE_EXTENSIONS",
    # Performance configuration defaults
    "DEFAULT_MAX_WORKERS",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_REQUEST_TIMEOUT",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_DELAY",
    # Logging configuration defaults
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_LOG_FILE",
    # GitHub configuration defaults
    "DEFAULT_GITHUB_API_BASE_URL",
    "DEFAULT_GITHUB_RATE_LIMIT_DELAY",
    # LM Studio configuration defaults
    "DEFAULT_LM_STUDIO_BASE_URL",
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
    # Configuration
    "ConfigManager",
    "create_config_manager",
]
