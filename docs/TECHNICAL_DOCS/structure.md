# SigmaHQ RAG Application - Code Structure Documentation

This document provides a comprehensive overview of the Python code structure and logic for the SigmaHQ RAG application.

## Table of Contents

1. [Application Architecture](#application-architecture)
2. [Core Services](#core-services)
3. [Models and Data Services](#models-and-data-services)
4. [Infrastructure Layer](#infrastructure-layer)
5. [Presentation Layer](#presentation-layer)
6. [Shared Utilities](#shared-utilities)
7. [Configuration Structure](#configuration-structure)

## Application Architecture

### Overview
The SigmaHQ RAG application follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Gradio App    │  │   Components    │  │   Interface  │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   App Factory   │  │   Config Mgmt   │  │   Services   │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                       Core Services                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   LLM Service   │  │   RAG Service   │  │   Chat Mgmt  │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Database      │  │   File Storage  │  │   LM Studio  │ │
│  │   Setup         │  │   Setup         │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Shared Utilities                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Constants     │  │   Exceptions    │  │   Utils      │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Entry Points

#### `main.py`
- **Purpose**: Main application entry point
- **Features**:
  - Command-line argument parsing
  - Signal handling for graceful shutdown
  - Production environment setup
- **Key Functions**:
  - `main()`: Main entry point with mode detection
  - `signal_handler()`: Graceful shutdown handler

#### `src/application/application.py`
- **Purpose**: Main application class using Gradio's native async support
- **Features**:
  - Tabbed interface management
  - Service initialization and coordination
  - Streaming response handling
- **Key Classes**:
  - `SigmaHQApplication`: Main application class
  - `create_application()`: Factory function for app creation

## Core Services

### LLM Service (`src/core/llm_service.py`)

#### Purpose
Provides LLM functionality with OpenAI compatibility.

#### Key Features
- OpenAI-compatible API
- Performance optimizations
- Comprehensive error handling
- Caching support
- Rate limiting

#### Key Classes
- `LLMService`: Main LLM service class

### RAG Service (`src/core/rag_service.py`)

#### Purpose
Provides Retrieval-Augmented Generation functionality with ChromaDB integration.

#### Key Features
- Direct ChromaDB integration
- Better error handling and fallback mechanisms
- Integration with optimized LLM service
- Performance optimizations for real-time applications
- CPU-based embedding support (sentence-transformers/all-MiniLM-L6-v2)

### Chat Service (`src/models/rag_chat_service.py`)

#### Purpose
Integrates RAG functionality with the chat interface to provide context-aware responses.

#### Key Features
- RAG-enhanced chat responses
- Conversation history management
- Streaming response support
- Context-aware responses based on stored documents

## Models and Data Services

### Config Service (`src/models/config_service.py`)

#### Purpose
Manages application configuration with validation and defaults.

#### Key Features
- Configuration loading and validation
- Default value management
- Environment variable support
- Configuration persistence

### Data Service (`src/models/data_service.py`)

#### Purpose
Manages document data processing and storage.

#### Key Features
- Document processing pipeline
- File format support (PDF, DOCX, TXT)
- Data validation and cleaning
- Storage management

### Chat History Management
- **Location**: Built into `RAGChatService`
- **Storage**: SQLite database in `data/history/`
- **Features**: Conversation history persistence and retrieval

## Infrastructure Layer

### Database Setup (`src/infrastructure/database_setup.py`)
- **Purpose**: Handles database initialization and management
- **Database**: SQLite at `data/history/rag_history.db`

### LM Studio Setup (`src/infrastructure/lm_studio_setup.py`)
- **Purpose**: Handles LM Studio integration (optional)
- **Features**: Server detection, API validation, model checking

### File System Setup (`src/infrastructure/file_system_setup.py`)
- **Purpose**: Manages file system operations and storage
- **Features**: Directory creation, temporary file handling

## Presentation Layer

### Gradio Components (`src/components/`)

#### Chat Interface (`src/components/chat_interface.py`)
- **Purpose**: Main RAG chat interface component
- **Features**:
  - Streaming responses via generator functions
  - Document upload and processing
  - Conversation history display

#### Data Management (`src/components/data_management.py`)
- **Purpose**: Document management interface

#### GitHub Management (`src/components/github_management.py`)
- **Purpose**: GitHub repository integration

#### File Management (`src/components/file_management.py`)
- **Purpose**: File system management interface

#### Logs Viewer (`src/components/logs_viewer.py`)
- **Purpose**: Application logs interface

#### Config Management (`src/components/config_management.py`)
- **Purpose**: Configuration editing and validation

### Base Component (`src/components/base_component.py`)
- **Purpose**: Base class for all Gradio components

## Shared Utilities

### Constants (`src/shared/constants.py`)
- **Purpose**: Centralized configuration constants
- **Includes**: Default values, thresholds, error codes

### Exceptions (`src/shared/exceptions.py`)
- **Purpose**: Custom exception classes
- **Types**: ServiceError, ConfigurationError, FileProcessingError

### Config Manager (`src/shared/config_manager.py`)
- **Purpose**: Configuration management across application
- **Features**: Environment variables, config file loading, validation

### Utils (`src/shared/utils.py`)
- **Purpose**: Shared utility functions
- **Includes**: Path operations, file handling, formatting

## Configuration Structure

### Current Configuration File
The application uses `data/config.json`:

```json
{
  "application": {
    "name": "SigmaHQ RAG",
    "version": "1.0.0"
  },
  "network": {
    "ip": "127.0.0.1",
    "port": 8000,
    "timeout": 30
  },
  "repositories": [...],
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000,
    "base_url": "http://127.0.0.1:1234"
  },
  "ui_css": {
    "theme": "soft",
    "primary_color": "#4f46e5",
    "secondary_color": "#10b981"
  }
}
```

### Default Configuration (`src/application/application.py`)
```python
DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8002,
        "base_url": "http://localhost:1234"
    },
    "rag": {
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_size": 1000,
        "chunk_overlap": 200
    }
}
```

### Configuration Priority (Low to High)
1. Default configuration (hardcoded in application.py)
2. Configuration file (`data/config.json`)
3. Environment variables

## File Structure

```
sigmahqrag/
├── main.py                          # Entry point
├── pyproject.toml                   # Project dependencies
├── data/
│   ├── config.json                  # Main configuration
│   ├── history/                     # Chat history (SQLite)
│   └── models/                      # Model files
│       └── chroma_db/               # Vector database
├── src/
│   ├── application/
│   │   └── application.py           # Main application class
│   ├── components/                  # Gradio UI components
│   ├── core/                        # Core services
│   ├── infrastructure/              # Infrastructure setup
│   ├── models/                      # Domain models
│   └── shared/                      # Shared utilities
├── tests/                           # Test suite
└── logs/                            # Application logs
```

## Architecture Principles

1. **Layered Design**: Clear separation between presentation, application, core services, and infrastructure layers
2. **Dependency Injection**: Services injected where needed
3. **Configuration Management**: Centralized configuration with multiple sources
4. **Error Handling**: Consistent error handling patterns across all layers
5. **Async Support**: Leverages Gradio's native async support for streaming

## Development Workflow

### Code Organization
- Follow PEP 8 guidelines
- Use type hints for better documentation
- Document public APIs

### Testing Strategy
- Unit tests for individual components
- Integration tests for service interactions
- Test coverage via pytest