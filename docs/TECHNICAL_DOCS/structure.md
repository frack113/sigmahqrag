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

**Note:** Port management uses Gradio's built-in auto_reload feature with `launch(reload=True)`. No external port manager is required.
```

### Entry Points

#### `main.py` - Application Entry Point
- **Purpose**: Entry point that calls application layer
- **Import**: `from src.app import create_application, SigmaHQApplication`
- **Responsibilities**:
  - Validate `data/config.json` exists before starting (critical)
  - Create and configure the application instance
  - Handle graceful shutdown signals (SIGINT/SIGTERM)
- **Entry Function**: `main()` - called when running `uv run python main.py`

#### `src/app.py` - Application Core
- **Purpose**: Core application orchestration using Gradio
- **Key Class**: `SigmaHQApplication`
- **Factory Function**: `create_application(config_path)` - creates app instance

---

## Core Components

### Application Layer

#### SigmaHQApplication (`src/app.py`)
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
Centralized Configuration Manager using simple JSON operations.

**Key Features:**
- Direct file-based config storage with `data/config.json` (path is REQUIRED - no defaults)
- Environment variable support for `network.ip` and `network.port` only
- Validation helpers for CLI handlers
- Thread-safe read/write operations
- Raises `MissingConfigError` if file is missing, invalid JSON, or lacks required fields

**Configuration Access (NO fallbacks!):**
```python
# All values come from config.json - direct access raises KeyError if missing!
port = self.config_manager.get("network.port")
model = self.config_manager.get("llm.model")
base_url = self.config_manager.get("llm.base_url")
theme = self.config_manager.get("ui_css.theme")
```

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
- Integration with RAGService for context-aware responses

#### Local Embedding Service (`src/core/local_embedding_service.py`)
CPU-compatible embedding generation service.

**Key Features:**
- Uses `all-MiniLM-L6-v2` model
- No GPU required - optimized for CPU execution
- Loads model from `data/models/all-MiniLM-L6-v2.safetensors`

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

#### ChromaDB Vector Storage (`data/chroma_db/`)
- Stores document embeddings for RAG retrieval in SQLite vector store
- Uses `all-MiniLM-L6-v2` embedding model (CPU-compatible)
- Model file: `data/models/all-MiniLM-L6-v2.safetensors`

#### Logging (`data/logs/`)
- Application log files
- Location: `data/logs/app.log`

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
├── main.py                                    # Entry point - validates config.json, calls src.app
├── pyproject.toml                             # Project dependencies (uv package manager)
├── data/                                     # Data directory (root location)
│   ├── chroma_db/                             # ChromaDB vector database
│   │   └── chroma.sqlite3                     # SQLite vector store
│   ├── config.json                            # REQUIRED: Main configuration
│   ├── github/                                # Git repositories for cloning
│   ├── history/                               # Chat history database
│   │   └── rag_history.db                     # SQLite file
│   ├── local/                                 # Local file storage
│   └── logs/                                  # Application log files
│       └── app.log                            # Main application log
├── src/                                      # Source code directory
│   ├── __init__.py                            # Package init
│   └── app.py                                 # Main application - SigmaHQApplication class
├── tests/                                    # Test suite with pytest
│   ├── __init__.py
│   ├── conftest.py                            # Test fixtures
│   ├── run_tests.py                           # Test runner script
│   ├── test_integration.py                    # Integration tests
│   └── files/                                 # Test data files
├── .coveragerc                               # Coverage configuration
├── .gitignore                                # Git ignore rules
├── .python-version                           # Python version (uv)
├── LICENSE                                   # MIT license
├── README.md                                 # Project documentation
└── uv.lock                                   # Dependency lock file