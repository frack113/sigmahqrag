"""
Constants for SigmaHQ RAG application.

Provides centralized configuration constants used across the application.
NOTE: All runtime configuration values must come from data/config.json - no defaults fallback.
This file contains only infrastructure constants (types, patterns, status codes).
"""

from typing import Any

# === Application Identity (NOT defaults) ===
APP_NAME = "SigmaHQ RAG"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "A Retrieval-Augmented Generation (RAG) application for SigmaHQ."
AUTHOR = "SigmaHQ Team"
LICENSE_ = "MIT"

# Environment variables (keys only - values come from config.json or system)
ENV_LLM_MODEL = "LLM_MODEL"
ENV_LLM_BASE_URL = "LLM_BASE_URL"
ENV_LLM_TEMPERATURE = "LLM_TEMPERATURE"
ENV_LLM_MAX_TOKENS = "LLM_MAX_TOKENS"

# === File Patterns ===
LOG_FILE_PATTERN = "*.log"
TEMP_FILE_PATTERN = "*.tmp"
CONFIG_FILE_PATTERN = "*.json"
BACKUP_FILE_PATTERN = "*.bak"

# === HTTP Status Codes ===
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# === Content Types ===
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT = "text/plain"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"

# === Date/Time Formats ===
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
LOG_FORMAT = "%Y-%m-%d %H:%M:%S"

# === Processing States ===
PROCESSING_STATE_PENDING = "pending"
PROCESSING_STATE_PROCESSING = "processing"
PROCESSING_STATE_COMPLETED = "completed"
PROCESSING_STATE_FAILED = "failed"
PROCESSING_STATE_CANCELLED = "cancelled"

# === Cache Strategies ===
CACHE_STRATEGY_LRU = "lru"
CACHE_STRATEGY_FIFO = "fifo"
CACHE_STRATEGY_TTL = "ttl"
CACHE_STRATEGY_NONE = "none"

# === Database Types ===
DATABASE_TYPE_SQLITE = "sqlite"
DATABASE_TYPE_POSTGRESQL = "postgresql"
DATABASE_TYPE_MYSQL = "mysql"
DATABASE_TYPE_MONGODB = "mongodb"

# === Vector Store Types ===
VECTOR_STORE_TYPE_CHROMADB = "chromadb"
VECTOR_STORE_TYPE_PINECONE = "pinecone"
VECTOR_STORE_TYPE_WEAVIATE = "weaviate"
VECTOR_STORE_TYPE_QDRANT = "qdrant"

# === LLM Providers ===
LLM_PROVIDER_OPENAI = "openai"
LLM_PROVIDER_HUGGINGFACE = "huggingface"
LLM_PROVIDER_CUSTOM = "custom"

# === Authentication Types ===
AUTH_TYPE_NONE = "none"
AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_BEARER = "bearer"
AUTH_TYPE_BASIC = "basic"
AUTH_TYPE_OAUTH = "oauth"

# === Rate Limiting Strategies ===
RATE_LIMIT_STRATEGY_FIXED_WINDOW = "fixed_window"
RATE_LIMIT_STRATEGY_SLIDING_WINDOW = "sliding_window"
RATE_LIMIT_STRATEGY_TOKEN_BUCKET = "token_bucket"
RATE_LIMIT_STRATEGY_LEAKY_BUCKET = "leaky_bucket"

# === Compression Types ===
COMPRESSION_TYPE_NONE = "none"
COMPRESSION_TYPE_GZIP = "gzip"
COMPRESSION_TYPE_BZIP2 = "bzip2"
COMPRESSION_TYPE_LZMA = "lzma"
COMPRESSION_TYPE_ZSTD = "zstd"

# === Serialization Formats ===
SERIALIZATION_JSON = "json"
SERIALIZATION_PICKLE = "pickle"
SERIALIZATION_MSGPACK = "msgpack"
SERIALIZATION_PROTOBUF = "protobuf"

# === Monitoring Metrics ===
METRIC_RESPONSE_TIME = "response_time"
METRIC_THROUGHPUT = "throughput"
METRIC_ERROR_RATE = "error_rate"
METRIC_MEMORY_USAGE = "memory_usage"
METRIC_CPU_USAGE = "cpu_usage"

# === Alert Levels ===
ALERT_LEVEL_INFO = "info"
ALERT_LEVEL_WARNING = "warning"
ALERT_LEVEL_ERROR = "error"
ALERT_LEVEL_CRITICAL = "critical"

# === Notification Types ===
NOTIFICATION_EMAIL = "email"
NOTIFICATION_SLACK = "slack"
NOTIFICATION_TEAMS = "teams"
NOTIFICATION_WEBHOOK = "webhook"
NOTIFICATION_SMS = "sms"

# === Backup Types ===
BACKUP_TYPE_FULL = "full"
BACKUP_TYPE_INCREMENTAL = "incremental"
BACKUP_TYPE_DIFFERENTIAL = "differential"

# === Deployment Environments ===
ENVIRONMENT_DEVELOPMENT = "development"
ENVIRONMENT_TESTING = "testing"
ENVIRONMENT_STAGING = "staging"
ENVIRONMENT_PRODUCTION = "production"

# === Feature Flags ===
FEATURE_RAG_ENABLED = "rag_enabled"
FEATURE_STREAMING_ENABLED = "streaming_enabled"
FEATURE_CACHING_ENABLED = "caching_enabled"
FEATURE_FILE_UPLOAD_ENABLED = "file_upload_enabled"
FEATURE_AUTHENTICATION_ENABLED = "authentication_enabled"
FEATURE_RATE_LIMITING_ENABLED = "rate_limiting_enabled"
FEATURE_MONITORING_ENABLED = "monitoring_enabled"
FEATURE_LOGGING_ENABLED = "logging_enabled"

# === Configuration Validation Keys ===
REQUIRED_CONFIG_KEYS = [
    "network.ip",
    "network.port",
    "llm.model",
    "llm.base_url",
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
]

# === Configuration Types ===
CONFIG_TYPE_STRING = "string"
CONFIG_TYPE_INTEGER = "integer"
CONFIG_TYPE_FLOAT = "float"
CONFIG_TYPE_BOOLEAN = "boolean"
CONFIG_TYPE_LIST = "list"
CONFIG_TYPE_DICT = "dict"
CONFIG_TYPE_PATH = "path"
CONFIG_TYPE_URL = "url"
CONFIG_TYPE_EMAIL = "email"

# === Configuration Validation Rules ===
CONFIG_VALIDATION_RULES: dict[str, dict[str, Any]] = {
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
}

# === Error Codes ===
ERROR_CODE_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERROR_CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
ERROR_CODE_FILE_TOO_LARGE = "FILE_TOO_LARGE"
ERROR_CODE_UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
ERROR_CODE_RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
ERROR_CODE_TIMEOUT = "TIMEOUT"

# === Success Codes ===
SUCCESS_CODE_OK = "OK"
SUCCESS_CODE_CREATED = "CREATED"
SUCCESS_CODE_UPDATED = "UPDATED"
SUCCESS_CODE_DELETED = "DELETED"
SUCCESS_CODE_PROCESSED = "PROCESSED"

# === Status Codes ===
STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"
STATUS_DEGRADED = "degraded"
STATUS_STARTING = "starting"
STATUS_STOPPING = "stopping"
STATUS_STOPPED = "stopped"

# === Service Names ===
SERVICE_LLM = "llm_service"
SERVICE_RAG = "rag_service"
SERVICE_CHAT = "chat_service"
SERVICE_DATA = "data_service"
SERVICE_CONFIG = "config_service"
SERVICE_LOGGING = "logging_service"
SERVICE_DATABASE = "database_service"
SERVICE_FILE_PROCESSOR = "file_processor"
SERVICE_GITHUB = "github_service"
SERVICE_EMBEDDING = "embedding_service"

# === Configuration Sections ===
CONFIG_SECTION_NETWORK = "network"
CONFIG_SECTION_LLM = "llm"
CONFIG_SECTION_REPOSITORIES = "repositories"
CONFIG_SECTION_UI_CSS = "ui_css"

# === Application Events ===
EVENT_SERVICE_START = "service_start"
EVENT_SERVICE_STOP = "service_stop"
EVENT_SERVICE_ERROR = "service_error"
EVENT_REQUEST_START = "request_start"
EVENT_REQUEST_END = "request_end"
EVENT_FILE_UPLOAD = "file_upload"
EVENT_FILE_PROCESS = "file_process"
EVENT_CHAT_MESSAGE = "chat_message"
EVENT_RAG_QUERY = "rag_query"

# === Database Constants (SQLite) ===
DEFAULT_DB_MAX_CONNECTIONS = 10
DEFAULT_DB_PATH = "data/history/chat_history.db"
DEFAULT_DB_TIMEOUT = 5

# === Data Directory Paths ===
DATA_GITHUB_PATH = "data/github"
DATA_CHROMA_PATH = "data/chroma_db"
DATA_HISTORY_PATH = "data/history"
DATA_LOCAL_PATH = "data/local"
DATA_LOGS_PATH = "data/logs"
DATA_MODELS_PATH = "data/models"
TEMP_DIR_PATH = "temp"

# === Application Cache Keys ===
CACHE_KEY_EMBEDDINGS = "embeddings"
CACHE_KEY_RAG_RESULTS = "rag_results"
CACHE_KEY_LLM_RESPONSES = "llm_responses"
CACHE_KEY_FILE_PROCESSED = "file_processed"

# === Custom CSS for Gradio Interface ===
CUSTOM_CSS = """
    /* Dynamic JSON Editor - auto-expanding height */
    .compact-json-editor {
        font-size: 13px !important;
        line-height: 1.45 !important;
        min-width: 400px !important;
        max-height: none !important;
        overflow-y: auto !important;
        background-color: #f9f9f9 !important;
        border-radius: 4px !important;
    }

    /* JSON Editor Label - matching editor size */
    .json-editor-label {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #3b3b3b !important;
        padding-top: 8px !important;
        padding-bottom: 4px !important;
    }

    /* Compact Buttons */
    button[size="sm"] {
        padding: 6px 12px !important;
        font-size: 13px !important;
        height: auto !important;
    }

    /* Button container scaling */
    .github-container .row {
        gap: 4px !important;
        margin-bottom: 8px !important;
    }

    /* Validation Status - scrollable area */
    .validation-status-box {
        max-height: 200px !important;
        overflow-y: auto !important;
        white-space: pre-wrap !important;
        font-family: monospace !important;
        font-size: 13px !important;
    }

    /* Two-column row layout */
    .two-column-row {
        display: flex !important;
        align-items: stretch !important;
        gap: 16px !important;
    }

    /* Main column (left) */
    .main-column {
        flex: 1 1 100% !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 16px !important;
    }

    /* Narrow sidebar column (right) */
    .sidebar-column {
        width: 240px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 12px !important;
    }

    /* GitHub container main column layout */
    .github-container > :last-child {
        display: flex !important;
        align-items: stretch !important;
        gap: 16px !important;
        min-height: 400px !important;
    }

    /* Status row styling */
    .status-row {
        display: flex !important;
        width: calc(100% - 8px) !important;
    }
"""
