"""
Constants for SigmaHQ RAG application.

Provides centralized configuration constants used across the application.
"""

from typing import Any

# Application constants
APP_NAME = "SigmaHQ RAG"
APP_VERSION = "2026.02.27"
APP_DESCRIPTION = "SigmaHQ RAG application with document processing and LLM integration"

# Default configuration values
DEFAULT_LLM_MODEL = "qwen/qwen3.5-9b"
DEFAULT_LLM_BASE_URL = "http://localhost:1234"
DEFAULT_LLM_API_KEY = "lm-studio"
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_TOKENS = 512
DEFAULT_LLM_ENABLE_STREAMING = True

# RAG configuration
DEFAULT_EMBEDDING_MODEL = "text-embedding-all-minilm-l6-v2-embedding"
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_RAG_N_RESULTS = 3
DEFAULT_RAG_MIN_SCORE = 0.1
DEFAULT_RAG_COLLECTION_NAME = "rag_collection"
DEFAULT_RAG_PERSIST_DIRECTORY = ".chromadb"

# Database configuration
DEFAULT_DB_PATH = "data/chat_history.db"
DEFAULT_DB_MAX_CONNECTIONS = 5
DEFAULT_DB_TIMEOUT = 30

# Cache configuration
DEFAULT_CACHE_SIZE = 1000
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_CACHE_ENABLED = True

# File processing configuration
DEFAULT_MAX_FILE_SIZE_MB = 50
DEFAULT_ALLOWED_FILE_EXTENSIONS = [
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".doc",
    ".csv",
    ".json",
    ".xml",
]
DEFAULT_TEMP_DIR = "temp/"
DEFAULT_UPLOAD_DIR = "uploads/"

# Performance configuration
DEFAULT_MAX_WORKERS = 4
DEFAULT_BATCH_SIZE = 10
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 1.0

# Logging configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_FILE = "logs/app.log"
DEFAULT_LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_LOG_BACKUP_COUNT = 5

# Security configuration
DEFAULT_RATE_LIMIT_CALLS = 100
DEFAULT_RATE_LIMIT_WINDOW = 60  # 1 minute
DEFAULT_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_ALLOWED_MIME_TYPES = [
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/csv",
    "application/json",
    "application/xml",
]

# Chat configuration
DEFAULT_CONVERSATION_HISTORY_LIMIT = 10
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Provide clear, concise, and accurate responses."
)
DEFAULT_STREAMING_ENABLED = True

# Error handling configuration
DEFAULT_ERROR_MESSAGE = (
    "An error occurred while processing your request. Please try again."
)
DEFAULT_TIMEOUT_MESSAGE = "The request timed out. Please try again."
DEFAULT_RETRY_MESSAGE = "Retrying request..."

# UI configuration
DEFAULT_UI_THEME = "soft"
DEFAULT_UI_TITLE = "SigmaHQ RAG"
DEFAULT_UI_FAVICON = "favicon.ico"
DEFAULT_UI_ANALYTICS_ENABLED = False

# Service configuration
DEFAULT_SERVICE_HEALTH_CHECK_INTERVAL = 60  # 1 minute
DEFAULT_SERVICE_TIMEOUT = 300  # 5 minutes
DEFAULT_SERVICE_RETRY_DELAY = 5.0

# Environment variables
ENV_LLM_MODEL = "LLM_MODEL"
ENV_LLM_BASE_URL = "LLM_BASE_URL"
ENV_LLM_API_KEY = "LLM_API_KEY"
ENV_LLM_TEMPERATURE = "LLM_TEMPERATURE"
ENV_LLM_MAX_TOKENS = "LLM_MAX_TOKENS"
ENV_RAG_ENABLED = "RAG_ENABLED"
ENV_RAG_N_RESULTS = "RAG_N_RESULTS"
ENV_RAG_MIN_SCORE = "RAG_MIN_SCORE"
ENV_DB_PATH = "DB_PATH"
ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_DEBUG_MODE = "DEBUG"
ENV_GITHUB_TOKEN = "GITHUB_TOKEN"
ENV_GITHUB_API_BASE_URL = "GITHUB_API_BASE_URL"

# File patterns
LOG_FILE_PATTERN = "*.log"
TEMP_FILE_PATTERN = "*.tmp"
CONFIG_FILE_PATTERN = "*.json"
BACKUP_FILE_PATTERN = "*.bak"

# HTTP status codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# Content types
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT = "text/plain"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"

# Date formats
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
LOG_FORMAT = "%Y-%m-%d %H:%M:%S"

# Validation patterns
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
URL_PATTERN = r"^https?://[^\s/$.?#].[^\s]*$"
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# Performance thresholds
MAX_RESPONSE_TIME = 30.0  # seconds
MAX_MEMORY_USAGE = 1024.0  # MB
MAX_CPU_USAGE = 80.0  # percentage

# Cache keys
CACHE_KEY_EMBEDDINGS = "embeddings"
CACHE_KEY_RAG_RESULTS = "rag_results"
CACHE_KEY_LLM_RESPONSES = "llm_responses"
CACHE_KEY_FILE_PROCESSED = "file_processed"

# Service names
SERVICE_LLM = "llm_service"
SERVICE_RAG = "rag_service"
SERVICE_CHAT = "chat_service"
SERVICE_DATA = "data_service"
SERVICE_CONFIG = "config_service"
SERVICE_LOGGING = "logging_service"
SERVICE_DATABASE = "database_service"
SERVICE_FILE_PROCESSOR = "file_processor"
SERVICE_FILE_STORAGE = "file_storage"
SERVICE_GITHUB = "github_service"
SERVICE_LM_STUDIO = "lm_studio_service"
SERVICE_EMBEDDING = "embedding_service"
SERVICE_APPLICATION = "application_service"

# GitHub configuration
DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"
DEFAULT_GITHUB_RATE_LIMIT_DELAY = 1.0

# LM Studio configuration
DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234"

# Event types
EVENT_SERVICE_START = "service_start"
EVENT_SERVICE_STOP = "service_stop"
EVENT_SERVICE_ERROR = "service_error"
EVENT_REQUEST_START = "request_start"
EVENT_REQUEST_END = "request_end"
EVENT_FILE_UPLOAD = "file_upload"
EVENT_FILE_PROCESS = "file_process"
EVENT_CHAT_MESSAGE = "chat_message"
EVENT_RAG_QUERY = "rag_query"

# Configuration sections
CONFIG_SECTION_LLM = "llm"
CONFIG_SECTION_RAG = "rag"
CONFIG_SECTION_DATABASE = "database"
CONFIG_SECTION_CACHE = "cache"
CONFIG_SECTION_LOGGING = "logging"
CONFIG_SECTION_SECURITY = "security"
CONFIG_SECTION_PERFORMANCE = "performance"

# Default configuration structure
DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {
        "model": DEFAULT_LLM_MODEL,
        "base_url": DEFAULT_LLM_BASE_URL,
        "api_key": DEFAULT_LLM_API_KEY,
        "temperature": DEFAULT_LLM_TEMPERATURE,
        "max_tokens": DEFAULT_LLM_MAX_TOKENS,
        "enable_streaming": DEFAULT_LLM_ENABLE_STREAMING,
    },
    "rag": {
        "enabled": True,
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        "n_results": DEFAULT_RAG_N_RESULTS,
        "min_score": DEFAULT_RAG_MIN_SCORE,
        "collection_name": DEFAULT_RAG_COLLECTION_NAME,
        "persist_directory": DEFAULT_RAG_PERSIST_DIRECTORY,
    },
    "database": {
        "path": DEFAULT_DB_PATH,
        "max_connections": DEFAULT_DB_MAX_CONNECTIONS,
        "timeout": DEFAULT_DB_TIMEOUT,
    },
    "cache": {
        "enabled": DEFAULT_CACHE_ENABLED,
        "size": DEFAULT_CACHE_SIZE,
        "ttl": DEFAULT_CACHE_TTL,
    },
    "logging": {
        "level": DEFAULT_LOG_LEVEL,
        "format": DEFAULT_LOG_FORMAT,
        "file": DEFAULT_LOG_FILE,
        "max_size": DEFAULT_LOG_MAX_SIZE,
        "backup_count": DEFAULT_LOG_BACKUP_COUNT,
    },
    "security": {
        "rate_limit_calls": DEFAULT_RATE_LIMIT_CALLS,
        "rate_limit_window": DEFAULT_RATE_LIMIT_WINDOW,
        "max_upload_size": DEFAULT_MAX_UPLOAD_SIZE,
        "allowed_mime_types": DEFAULT_ALLOWED_MIME_TYPES,
    },
    "performance": {
        "max_workers": DEFAULT_MAX_WORKERS,
        "batch_size": DEFAULT_BATCH_SIZE,
        "request_timeout": DEFAULT_REQUEST_TIMEOUT,
        "retry_attempts": DEFAULT_RETRY_ATTEMPTS,
        "retry_delay": DEFAULT_RETRY_DELAY,
    },
    "ui": {
        "theme": DEFAULT_UI_THEME,
        "title": DEFAULT_UI_TITLE,
        "favicon": DEFAULT_UI_FAVICON,
        "analytics_enabled": DEFAULT_UI_ANALYTICS_ENABLED,
    },
    "chat": {
        "history_limit": DEFAULT_CONVERSATION_HISTORY_LIMIT,
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "streaming_enabled": DEFAULT_STREAMING_ENABLED,
    },
}

# Error codes
ERROR_CODE_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
ERROR_CODE_FILE_TOO_LARGE = "FILE_TOO_LARGE"
ERROR_CODE_UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
ERROR_CODE_RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
ERROR_CODE_TIMEOUT = "TIMEOUT"
ERROR_CODE_AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
ERROR_CODE_AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
ERROR_CODE_INTERNAL_ERROR = "INTERNAL_ERROR"

# Success codes
SUCCESS_CODE_OK = "OK"
SUCCESS_CODE_CREATED = "CREATED"
SUCCESS_CODE_UPDATED = "UPDATED"
SUCCESS_CODE_DELETED = "DELETED"
SUCCESS_CODE_PROCESSED = "PROCESSED"

# Status codes
STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"
STATUS_DEGRADED = "degraded"
STATUS_STARTING = "starting"
STATUS_STOPPING = "stopping"
STATUS_STOPPED = "stopped"

# File types
FILE_TYPE_TEXT = "text"
FILE_TYPE_DOCUMENT = "document"
FILE_TYPE_SPREADSHEET = "spreadsheet"
FILE_TYPE_PRESENTATION = "presentation"
FILE_TYPE_IMAGE = "image"
FILE_TYPE_AUDIO = "audio"
FILE_TYPE_VIDEO = "video"
FILE_TYPE_ARCHIVE = "archive"
FILE_TYPE_CODE = "code"
FILE_TYPE_DATA = "data"

# Document types
DOCUMENT_TYPE_PDF = "pdf"
DOCUMENT_TYPE_WORD = "word"
DOCUMENT_TYPE_EXCEL = "excel"
DOCUMENT_TYPE_POWERPOINT = "powerpoint"
DOCUMENT_TYPE_TEXT = "text"
DOCUMENT_TYPE_MARKDOWN = "markdown"
DOCUMENT_TYPE_CODE = "code"

# Processing states
PROCESSING_STATE_PENDING = "pending"
PROCESSING_STATE_PROCESSING = "processing"
PROCESSING_STATE_COMPLETED = "completed"
PROCESSING_STATE_FAILED = "failed"
PROCESSING_STATE_CANCELLED = "cancelled"

# Cache strategies
CACHE_STRATEGY_LRU = "lru"
CACHE_STRATEGY_FIFO = "fifo"
CACHE_STRATEGY_TTL = "ttl"
CACHE_STRATEGY_NONE = "none"

# Database types
DATABASE_TYPE_SQLITE = "sqlite"
DATABASE_TYPE_POSTGRESQL = "postgresql"
DATABASE_TYPE_MYSQL = "mysql"
DATABASE_TYPE_MONGODB = "mongodb"

# Vector store types
VECTOR_STORE_TYPE_CHROMADB = "chromadb"
VECTOR_STORE_TYPE_PINECONE = "pinecone"
VECTOR_STORE_TYPE_WEAVIATE = "weaviate"
VECTOR_STORE_TYPE_QDRANT = "qdrant"

# Embedding types
EMBEDDING_TYPE_OPENAI = "openai"
EMBEDDING_TYPE_HUGGINGFACE = "huggingface"
EMBEDDING_TYPE_CUSTOM = "custom"

# LLM providers
LLM_PROVIDER_OPENAI = "openai"
LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_HUGGINGFACE = "huggingface"
LLM_PROVIDER_CUSTOM = "custom"
LLM_PROVIDER_LM_STUDIO = "lm_studio"

# Authentication types
AUTH_TYPE_NONE = "none"
AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_BEARER = "bearer"
AUTH_TYPE_BASIC = "basic"
AUTH_TYPE_OAUTH = "oauth"

# Rate limiting strategies
RATE_LIMIT_STRATEGY_FIXED_WINDOW = "fixed_window"
RATE_LIMIT_STRATEGY_SLIDING_WINDOW = "sliding_window"
RATE_LIMIT_STRATEGY_TOKEN_BUCKET = "token_bucket"
RATE_LIMIT_STRATEGY_LEAKY_BUCKET = "leaky_bucket"

# Compression types
COMPRESSION_TYPE_NONE = "none"
COMPRESSION_TYPE_GZIP = "gzip"
COMPRESSION_TYPE_BZIP2 = "bzip2"
COMPRESSION_TYPE_LZMA = "lzma"
COMPRESSION_TYPE_ZSTD = "zstd"

# Serialization formats
SERIALIZATION_JSON = "json"
SERIALIZATION_PICKLE = "pickle"
SERIALIZATION_MSGPACK = "msgpack"
SERIALIZATION_PROTOBUF = "protobuf"

# Monitoring metrics
METRIC_RESPONSE_TIME = "response_time"
METRIC_THROUGHPUT = "throughput"
METRIC_ERROR_RATE = "error_rate"
METRIC_MEMORY_USAGE = "memory_usage"
METRIC_CPU_USAGE = "cpu_usage"
METRIC_CACHE_HIT_RATE = "cache_hit_rate"
METRIC_DATABASE_CONNECTIONS = "database_connections"
METRIC_ACTIVE_USERS = "active_users"
METRIC_REQUEST_COUNT = "request_count"
METRIC_FILE_PROCESSED = "file_processed"

# Alert levels
ALERT_LEVEL_INFO = "info"
ALERT_LEVEL_WARNING = "warning"
ALERT_LEVEL_ERROR = "error"
ALERT_LEVEL_CRITICAL = "critical"

# Notification types
NOTIFICATION_EMAIL = "email"
NOTIFICATION_SLACK = "slack"
NOTIFICATION_TEAMS = "teams"
NOTIFICATION_WEBHOOK = "webhook"
NOTIFICATION_SMS = "sms"

# Backup types
BACKUP_TYPE_FULL = "full"
BACKUP_TYPE_INCREMENTAL = "incremental"
BACKUP_TYPE_DIFFERENTIAL = "differential"

# Deployment environments
ENVIRONMENT_DEVELOPMENT = "development"
ENVIRONMENT_TESTING = "testing"
ENVIRONMENT_STAGING = "staging"
ENVIRONMENT_PRODUCTION = "production"

# Feature flags
FEATURE_RAG_ENABLED = "rag_enabled"
FEATURE_STREAMING_ENABLED = "streaming_enabled"
FEATURE_CACHING_ENABLED = "caching_enabled"
FEATURE_FILE_UPLOAD_ENABLED = "file_upload_enabled"
FEATURE_AUTHENTICATION_ENABLED = "authentication_enabled"
FEATURE_RATE_LIMITING_ENABLED = "rate_limiting_enabled"
FEATURE_MONITORING_ENABLED = "monitoring_enabled"
FEATURE_LOGGING_ENABLED = "logging_enabled"

# Configuration validation
REQUIRED_CONFIG_KEYS = [
    "llm.model",
    "llm.base_url",
    "llm.api_key",
    "database.path",
    "logging.level",
]

OPTIONAL_CONFIG_KEYS = [
    "llm.temperature",
    "llm.max_tokens",
    "llm.enable_streaming",
    "rag.enabled",
    "rag.embedding_model",
    "rag.chunk_size",
    "rag.chunk_overlap",
    "rag.n_results",
    "rag.min_score",
    "cache.enabled",
    "cache.size",
    "cache.ttl",
]

# Configuration types
CONFIG_TYPE_STRING = "string"
CONFIG_TYPE_INTEGER = "integer"
CONFIG_TYPE_FLOAT = "float"
CONFIG_TYPE_BOOLEAN = "boolean"
CONFIG_TYPE_LIST = "list"
CONFIG_TYPE_DICT = "dict"
CONFIG_TYPE_PATH = "path"
CONFIG_TYPE_URL = "url"
CONFIG_TYPE_EMAIL = "email"

# Configuration validation rules
CONFIG_VALIDATION_RULES = {
    "llm.temperature": {
        "type": CONFIG_TYPE_FLOAT,
        "min": 0.0,
        "max": 2.0,
    },
    "llm.max_tokens": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 1,
        "max": 8192,
    },
    "llm.enable_streaming": {
        "type": CONFIG_TYPE_BOOLEAN,
    },
    "rag.chunk_size": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 100,
        "max": 10000,
    },
    "rag.chunk_overlap": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 0,
        "max": 1000,
    },
    "rag.n_results": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 1,
        "max": 100,
    },
    "rag.min_score": {
        "type": CONFIG_TYPE_FLOAT,
        "min": 0.0,
        "max": 1.0,
    },
    "cache.size": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 1,
        "max": 100000,
    },
    "cache.ttl": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 1,
        "max": 86400,  # 24 hours
    },
    "database.timeout": {
        "type": CONFIG_TYPE_INTEGER,
        "min": 1,
        "max": 300,
    },
    "logging.level": {
        "type": CONFIG_TYPE_STRING,
        "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    },
}
