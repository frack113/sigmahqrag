# SigmaHQ RAG - Technical Architecture

**Version:** 2.0  
**Last Updated:** 2026-03-14  

---

## Configuration Requirements

### ⚠️ Critical: No Defaults Policy

Before running the application, `data/config.json` **MUST exist**. There are **NO fallback defaults** - all configuration values come exclusively from this file. If any required field is missing, the application will fail to start with a clear error message.

### Required Configuration Structure

```json
{
  "network": {
    "ip": "127.0.0.1",
    "port": 8000,
    "auto_reload": true
  },
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000,
    "base_url": "http://127.0.0.1:1234"
  },
  "repositories": [...],
  "ui_css": {
    "theme": "soft",
    "title": "SigmaHQ RAG"
  }
}
```

### Configuration Priority

| Priority | Source | Description |
|----------|--------|-------------|
| 1 (Required) | `data/config.json` | All mandatory configuration - application will NOT start without this |
| 2 (Override) | Environment variables | Only allowed for `network.ip` and `network.port` |

---

## Architecture Overview

### Layered Design Pattern

The application follows a clear separation of concerns with four distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer (Gradio)                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐│
│  │   Chat Interface │  │ Data Management  │  │ GitHub Mgmt ││
│  └──────────────────┘  └──────────────────┘  └─────────────┘│
└─────────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │SigmaHQApplication│ │   ConfigManager  │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Services                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐│
│  │     RAG Service │  │    LLM Service   │  │ Chat Service││
│  └──────────────────┘  └──────────────────┘  └─────────────┘│
└─────────────────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                        │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   SQLite DB      │  │ ChromaDB Vector  │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Entry Points

#### `main.py`
- **Purpose**: Application entry point with validation
- **Responsibilities**:
  - Validate `data/config.json` exists before starting (critical)
  - Create and configure the application instance
  - Handle graceful shutdown signals (SIGINT/SIGTERM)
- **Entry Function**: `main()` - called when running `uv run python main.py`

#### `src/application/application.py`
- **Purpose**: Core application orchestration using Gradio
- **Key Class**: `SigmaHQApplication`
- **Factory Function**: `create_application(config_path)` - creates app instance

---

## Core Components

### Application Layer

#### SigmaHQApplication (`src/application/application.py`)
The main orchestrator that ties everything together with Gradio UI.

**Key Responsibilities:**
1. **Configuration Loading**: Loads and validates `data/config.json` at startup
2. **Service Initialization**: Creates RAG service, data service, and chat components
3. **UI Orchestration**: Builds Gradio interface with tabs for all features
4. **Server Launch**: Configures and starts the Gradio server

**Key Methods:**
- `__init__(config_path)`: Initialize with config validation (raises error if missing)
- `create_interface()`: Build Gradio UI with all functional tabs
- `launch(...)`: Start the web server with configured settings
- `cleanup()`: Graceful shutdown handling

**Configuration Access (NO fallbacks!):**
```python
# All values come from config.json - direct access raises KeyError if missing!
port = self.config["network"]["port"]
model = self.config["llm"]["model"]
base_url = self.config["llm"]["base_url"]
theme = self.config["ui_css"]["theme"]
```

#### ConfigManager (`src/shared/config_manager.py`)
Handles configuration loading, validation, and manipulation with strict no-defaults policy.

**Key Features:**
- Loads from `data/config.json` (path is REQUIRED - no defaults)
- Validates all required fields are present before allowing any operations
- Provides typed access to nested config values via dot notation: `config.get("network.port")`
- Supports environment variable overrides for `network.ip` and `network.port` only
- Raises `MissingConfigError` if file is missing, invalid JSON, or lacks required fields

**Required Config Sections (all mandatory):**
| Section | Required Fields | Purpose |
|---------|----------------|---------|
| `network` | ip, port, auto_reload | Server network settings |
| `llm` | model, base_url, temperature, max_tokens | LLM configuration |
| `repositories` | url, branch, enabled, file_extensions[] | GitHub repos to index |
| `ui_css` | theme, title | UI customization |

---

### Core Services

#### RAG Service (`src/core/rag_service.py`)
Provides Retrieval-Augmented Generation functionality with ChromaDB integration.

**Key Features:**
- Document chunking and embedding generation
- Vector storage in ChromaDB database
- Semantic search and relevance-based retrieval
- Integration with LLM service for context-aware responses
- CPU-compatible embedding model: `all-MiniLM-L6-v2`

#### LLM Service (`src/core/llm_service.py`)
OpenAI-compatible interface for the configured LLM model.

**Key Features:**
- Streaming response support for real-time chat
- Temperature control for output randomness
- Token limit management (configurable via config.json)
- Caching support for improved performance
- Rate limiting prevention

#### Chat Service (`src/core/chat_service.py`)
Integrates RAG functionality with conversational chat interface.

**Key Features:**
- Context-aware responses using retrieved documents
- Conversation history management
- Streaming response to user interface

---

### Presentation Layer (Gradio Components)

All UI components use Gradio exclusively - no other frameworks allowed.

| Component | File | Purpose |
|-----------|------|---------|
| ChatInterface | `src/components/chat_interface.py` | Main chat with streaming responses and document upload |
| DataManagement | `src/components/data_management.py` | Document upload, processing, and deletion |
| GitHubManagement | `src/components/github_management.py` | Repository configuration and management |
| FileManagement | `src/components/file_management.py` | Local file browser and operations |
| ConfigManagement | `src/components/config_management.py` | Configuration editor with validation |
| LogsViewer | `src/components/logs_viewer.py` | Application logs display and filtering |

---

### Infrastructure Layer

#### Database Management (`src/infrastructure/database/`)
- SQLite-based chat history storage
- Location: `data/history/rag_history.db`
- Manages conversation history persistence

#### ChromaDB Vector Storage (`data/models/chroma_db/`)
- Stores document embeddings for RAG retrieval
- Uses `all-MiniLM-L6-v2` embedding model (CPU-compatible)
- Model file: `data/models/all-MiniLM-L6-v2.safetensors`

#### LM Studio Integration (`src/infrastructure/lm_studio_setup.py`)
- Optional local LLM server integration
- Server detection and API validation
- Model availability checking

---

## Development Guidelines

### 📋 Gradio-Only Rule

All user interfaces **MUST** use Gradio components. No FastAPI templates, Streamlit, Dash, or other frameworks are allowed.

**Correct Usage:**
```python
import gradio as gr

def create_ui():
    with gr.Blocks() as app:
        gr.Markdown("# SigmaHQ RAG")
        gr.Chatbot()
        gr.File()
        gr.Button("Submit")
    
    return app
```

**Incorrect Usage (VIOLATION):**
```python
from fastapi import FastAPI  # ❌ NOT ALLOWED!
import streamlit as st       # ❌ NOT ALLOWED!
app = Dash(...)              # ❌ NOT ALLOWED!
```

### 📋 No Fallback Defaults Rule

The application uses **exclusively** `data/config.json`. There are NO fallback values, NO DEFAULT_* constants, and NO hardcoded defaults.

**Correct Usage:**
```python
# Direct access - raises KeyError if missing (required behavior)
port = config["network"]["port"]
model = llm_config["model"]
base_url = llm_config["base_url"]
```

**Incorrect Usage (VIOLATION):**
```python
port = config.get("network.port", 8000)        # ❌ NO FALLBACKS!
DEFAULT_PORT = 8000                             # ❌ FORBIDDEN!
host = "localhost"                              # ❌ HARDCODED!
model = llm_config.get("model", "gpt-3.5")     # ❌ FORBIDDEN!
```

### File Structure

```
sigmahqrag/
├── main.py                          # Entry point - validates config.json exists
├── pyproject.toml                   # Project dependencies (uv package manager)
├── data/
│   ├── config.json                  # REQUIRED: Main configuration (NO fallbacks allowed)
│   ├── history/                     # Chat history database
│   │   └── rag_history.db           # SQLite file
│   ├── models/                      # ML models & vector storage
│   │   ├── all-MiniLM-L6-v2.safetensors  # Embedding model
│   │   └── chroma_db/               # Vector database (ChromaDB)
│   ├── github.json                  # Cached GitHub repository data
│   └── local/                       # Local file storage
├── src/
│   ├── application/                 # Application orchestration layer
│   │   ├── __init__.py
│   │   └── application.py           # SigmaHQApplication class (Gradio app)
│   ├── components/                  # Gradio UI components (presentation layer)
│   │   ├── __init__.py
│   │   ├── base_component.py        # Base class for UI components
│   │   ├── chat_interface.py        # Main chat interface
│   │   ├── config_management.py     # Config editor UI
│   │   ├── data_management.py       # Document management UI
│   │   ├── file_management.py       # File browser UI
│   │   ├── github_management.py     # GitHub repo management UI
│   │   └── logs_viewer.py           # Logs display UI
│   ├── core/                        # Core business services layer
│   │   ├── __init__.py
│   │   ├── chat_service.py          # Chat + RAG integration
│   │   ├── llm_service.py           # LLM interface (OpenAI-compatible)
│   │   ├── local_embedding_service.py # CPU embedding model
│   │   └── rag_service.py           # RAG pipeline service
│   ├── infrastructure/              # Infrastructure setup layer
│   │   ├── __init__.py
│   │   ├── database_setup.py        # SQLite initialization
│   │   ├── environment_setup.py     # Environment configuration
│   │   ├── file_storage_setup.py    # File storage setup
│   │   ├── lm_studio_setup.py       # LM Studio integration
│   │   ├── port_manager.py          # Port conflict detection
│   │   └── service_lifecycle.py     # Service start/stop management
│   │   ├── database/                # Database utilities
│   │   │   ├── __init__.py
│   │   │   └── sqlite_manager.py    # SQLite operations
│   │   └── external/                # External service clients
│   │       ├── __init__.py
│   │       ├── github_client.py     # GitHub API client
│   │       └── lm_studio_client.py  # LM Studio API client
│   ├── models/                      # Domain models layer
│   │   ├── __init__.py
│   │   ├── config_service.py        # Configuration service wrapper
│   │   ├── data_service.py          # Document processing service
│   │   ├── logging_service.py       # Log management service
│   │   └── rag_chat_service.py      # RAG-enhanced chat service
│   └── shared/                      # Shared utilities layer
│       ├── __init__.py
│       ├── base_service.py          # Base service class
│       ├── config_manager.py        # Configuration management (REQUIRED at startup)
│       ├── constants.py             # Application constants
│       ├── exceptions.py            # Custom exceptions (MissingConfigError, etc.)
│       ├── statistics.py            # Statistics tracking
│       ├── stats_manager.py         # Stats management
│       ├── types.py                 # Type definitions
│       └── utils.py                 # Utility functions
├── tests/                           # Test suite with pytest
│   ├── __init__.py
│   ├── conftest.py                  # Test fixtures
│   ├── run_tests.py                 # Test runner script
│   ├── test_integration.py          # Integration tests
│   ├── test_lm_studio_integration.py # LM Studio tests
│   └── files/                       # Test data files
├── logs/                            # Application log files
├── .coveragerc                      # Coverage configuration
├── .gitignore                       # Git ignore rules
├── .python-version                 # Python version (uv)
├── LICENSE                          # MIT license
├── README.md                        # Project documentation
└── uv.lock                          # Dependency lock file
```

---

## Quick Reference

| Concept | Location | Purpose |
|---------|----------|---------|
| Configuration file | `data/config.json` | All application configuration (REQUIRED) |
| Application entry | `main.py` | Entry point with config validation |
| Main application class | `src/application/application.py` | Gradio app orchestration |
| Config manager | `src/shared/config_manager.py` | Configuration loading/validation |
| Gradio components | `src/components/*.py` | UI tabs and features |
| RAG service | `src/core/rag_service.py` | RAG pipeline implementation |
| LLM service | `src/core/llm_service.py` | LLM interface |
| Database setup | `src/infrastructure/database_setup.py` | SQLite initialization |

---

## Configuration Validation Flow

```
┌─────────────────────────────────────┐
│  Application Start (main.py)        │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Validate data/config.json exists   │ ← MISSING → Exit with error
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Load and parse JSON                │ ← INVALID → Exit with error
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Validate required fields present   │ ← MISSING → Exit with error
│  • network.ip, port, auto_reload    │
│  • llm.model, base_url, etc.        │
│  • repositories[]                   │
│  • ui_css.theme                     │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Create SigmaHQApplication          │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Launch Gradio Server               │
└─────────────────────────────────────┘
```

---

## Error Handling Guidelines

### Missing Configuration Error
When `data/config.json` is missing or invalid:
```python
from src.shared.config_manager import MissingConfigError

try:
    app = SigmaHQApplication(config_path="data/config.json")
except MissingConfigError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)  # Do not start application
```

### Configuration Access Error
When accessing a missing config field (should never happen if validation passes):
```python
# This raises KeyError - should be caught during development/CI
port = config["network"]["port"]  # Raises KeyError if 'network' or 'port' missing
```

---

## Testing with Tests

Run the test suite:
```bash
uv run pytest tests/
```

Required test dependencies (install via uv):
```bash
uv add pytest pytest-asyncio httpx chromadb
```

---

## Development Workflow

### 1. Start Development Server
```bash
uv run python main.py
```

### 2. Run Linters and Type Checkers
```bash
uvx black src/ tests/
uvx ruff check src/ tests/
uvx mypy src/
```

### 3. Run Tests
```bash
uv run pytest tests/ -v
```

### 4. Check Coverage
```bash
uv run pytest --cov=src tests/
```

---

## Resources

- **Main Documentation**: See `docs/` directory for user and deployment guides
- **Configuration Reference**: This document (`docs/TECHNICAL_DOCS/structure.md`)
- **Code Rules**: See `.clinerules/` directory for coding standards
- **Configuration Manager**: `src/shared/config_manager.py`
- **Main Entry Point**: `main.py`