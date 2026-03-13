# SigmaHQ RAG Application - Code Structure Documentation

This document provides a comprehensive overview of the Python code structure and logic for the SigmaHQ RAG application.

## Table of Contents

1. [Application Architecture](#application-architecture)
2. [Core Services](#core-services)
3. [Models and Data Services](#models-and-data-services)
4. [Infrastructure Layer](#infrastructure-layer)
5. [Presentation Layer](#presentation-layer)
6. [Shared Utilities](#shared-utilities)
7. [Configuration and Constants](#configuration-and-constants)
8. [File Processing](#file-processing)
9. [Error Handling and Monitoring](#error-handling-and-monitoring)
10. [Dependencies and External Services](#dependencies-and-external-services)

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
│  │   Database      │  │   File Storage  │  │   External   │ │
│  │   Setup         │  │   Setup         │  │   Services   │ │
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
- **Purpose**: Main application entry point with auto-reload support
- **Features**:
  - Command-line argument parsing
  - Development vs production mode detection
  - Signal handling for graceful shutdown
  - Production environment setup
- **Key Functions**:
  - `main()`: Main entry point with mode detection
  - `signal_handler()`: Graceful shutdown handler

#### `src/application/app.py`
- **Purpose**: Main Gradio application class
- **Features**:
  - Tabbed interface management
  - Service initialization and coordination
  - Async operation support
  - Streaming response handling
- **Key Classes**:
  - `SigmaHQGradioApp`: Main application class
  - `safe_llm_call()`: Safe wrapper for LLM calls

## Core Services

### LLM Service (`src/core/llm_service.py`)

#### Purpose
Provides LLM functionality with OpenAI compatibility, optimized for performance and ease of use.

#### Key Features
- OpenAI-compatible API
- Performance optimizations
- Comprehensive error handling
- Caching support
- Resource monitoring
- Rate limiting

#### Key Classes
- `LLMService`: Main LLM service class
- `LLMStats`: Statistics tracking for LLM operations

#### Key Methods
- `simple_completion()`: Optimized simple completion
- `streaming_completion()`: Streaming response generation
- `batch_completion()`: Process multiple prompts efficiently
- `check_availability()`: Service health check

#### Configuration
```python
LLMConfig = {
    'model': 'mistralai/ministral-3-14b-reasoning',
    'base_url': 'http://localhost:1234',
    'api_key': 'lm-studio',
    'temperature': 0.7,
    'max_tokens': 512,
    'enable_streaming': True
}
```

### RAG Service (`src/core/rag_service.py`)

#### Purpose
Provides Retrieval-Augmented Generation functionality with ChromaDB integration.

#### Key Features
- Direct ChromaDB integration
- Better error handling and fallback mechanisms
- Integration with optimized LLM service
- Performance optimizations for real-time applications
- Simplified API for common RAG operations
- Comprehensive caching

#### Key Classes
- `RAGService`: Main RAG service class
- `RAGStats`: Statistics tracking for RAG operations

#### Key Methods
- `generate_embeddings()`: Generate embeddings for text
- `store_context()`: Store document context in vector database
- `retrieve_context()`: Retrieve relevant context using similarity search
- `generate_rag_response()`: Generate RAG-enhanced responses
- `generate_streaming_rag_response()`: Streaming RAG responses

#### Configuration
```python
EmbeddingConfig = {
    'model': 'text-embedding-all-minilm-l6-v2-embedding',
    'base_url': 'http://localhost:1234',
    'api_key': 'lm-studio',
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'collection_name': 'chat_collection'
}
```

### Chat Service (`src/models/rag_chat_service.py`)

#### Purpose
Integrates RAG functionality with the chat interface to provide context-aware responses.

#### Key Features
- RAG-enhanced chat responses
- Conversation history management
- Streaming response support
- Context-aware responses based on stored documents

#### Key Classes
- `RAGChatService`: Main chat service class

#### Key Methods
- `generate_response()`: Generate chat responses with RAG
- `generate_streaming_response()`: Streaming chat responses
- `add_message_to_history()`: Manage conversation history
- `get_rag_status()`: Get RAG system status

## Models and Data Services

### Chat History Service (`src/models/chat_history_service.py`)

#### Purpose
Manages chat conversation history and persistence.

#### Key Features
- SQLite-based chat history storage
- Conversation management
- Message persistence
- History retrieval and cleanup

### Data Service (`src/models/data_service.py`)

#### Purpose
Manages document data processing and storage.

#### Key Features
- Document processing pipeline
- File format support (PDF, DOCX, TXT, etc.)
- Data validation and cleaning
- Storage management

### Config Service (`src/models/config_service.py`)

#### Purpose
Manages application configuration with validation and defaults.

#### Key Features
- Configuration loading and validation
- Default value management
- Environment variable support
- Configuration persistence

### File Processor (`src/models/file_processor.py`)

#### Purpose
Handles file processing and text extraction.

#### Key Features
- Multi-format file support
- Text extraction from documents
- Content preprocessing
- Error handling for corrupted files

## Infrastructure Layer

### Database Setup (`src/infrastructure/database_setup.py`)

#### Purpose
Handles database initialization and management.

#### Key Features
- SQLite database setup
- Schema creation and migration
- Connection pooling
- Database health monitoring

### File System Setup (`src/infrastructure/file_system_setup.py`)

#### Purpose
Manages file system operations and storage.

#### Key Features
- Directory structure creation
- File storage management
- Temporary file handling
- File system monitoring

### LM Studio Setup (`src/infrastructure/lm_studio_setup.py`)

#### Purpose
Handles LM Studio integration and configuration.

#### Key Features
- LM Studio server detection
- API endpoint validation
- Model availability checking
- Connection management

### Production Setup (`src/infrastructure/production_setup.py`)

#### Purpose
Handles production environment setup and configuration.

#### Key Features
- Production environment validation
- Service configuration
- Security setup
- Performance optimization

## Presentation Layer

### Gradio Components (`src/components/`)

#### Chat Interface (`src/components/chat_interface.py`)
- **Purpose**: Main chat interface component
- **Features**:
  - Multi-modal chat support
  - Document upload and processing
  - Conversation history display
  - Streaming response handling

#### Data Management (`src/components/data_management.py`)
- **Purpose**: Document management interface
- **Features**:
  - Document upload interface
  - Processing status display
  - Data validation
  - Error handling

#### Configuration Management (`src/components/config_management.py`)
- **Purpose**: Configuration interface
- **Features**:
  - Configuration editing
  - Validation and error display
  - Default value management
  - Configuration persistence

#### File Management (`src/components/file_management.py`)
- **Purpose**: File system management interface
- **Features**:
  - File listing and management
  - Upload and download functionality
  - File type validation
  - Storage monitoring

#### Logs Viewer (`src/components/logs_viewer.py`)
- **Purpose**: Application logs interface
- **Features**:
  - Real-time log display
  - Log filtering and search
  - Log level management
  - Log export functionality

### Base Component (`src/components/base_component.py`)

#### Purpose
Base class for all Gradio components with common functionality.

#### Key Features
- Common initialization patterns
- Error handling and logging
- Component lifecycle management
- Shared utility methods

## Shared Utilities

### Constants (`src/shared/constants.py`)

#### Purpose
Centralized configuration constants used across the application.

#### Key Categories
- Application configuration defaults
- Service configuration values
- File processing settings
- Performance thresholds
- Error codes and messages
- Status codes and states

### Exceptions (`src/shared/exceptions.py`)

#### Purpose
Custom exception classes for better error handling.

#### Key Exception Types
- `ServiceError`: Base service exception
- `ConfigurationError`: Configuration-related errors
- `FileProcessingError`: File processing failures
- `NetworkError`: Network connectivity issues
- `LLMError`: LLM service errors
- `RAGError`: RAG service errors

### Utils (`src/shared/utils.py`)

#### Purpose
Shared utility functions and helpers.

#### Key Functions
- `get_app_directory()`: Get application directory path
- `validate_file_type()`: File type validation
- `format_file_size()`: File size formatting
- `sanitize_filename()`: Filename sanitization
- `get_memory_usage()`: Memory usage monitoring
- `get_cpu_usage()`: CPU usage monitoring

### Base Service (`src/shared/base_service.py`)

#### Purpose
Base class for all services with common functionality.

#### Key Features
- Common initialization patterns
- Error handling and logging
- Service lifecycle management
- Configuration management
- Health check implementation

## Configuration and Constants

### Configuration Structure

The application uses a hierarchical configuration system:

1. **Default Configuration** (`src/shared/constants.py`)
   - Built-in default values
   - Environment-specific defaults

2. **File-based Configuration** (`data/config/`)
   - `environment.json`: Environment-specific settings
   - `production.json`: Production configuration
   - `lm_studio.json`: LM Studio settings

3. **Environment Variables**
   - Override configuration values
   - Support for deployment environments

4. **Runtime Configuration**
   - Command-line arguments
   - Dynamic configuration updates

### Key Configuration Sections

```json
{
  "llm": {
    "model": "mistralai/ministral-3-14b-reasoning",
    "base_url": "http://localhost:1234",
    "api_key": "lm-studio",
    "temperature": 0.7,
    "max_tokens": 512
  },
  "rag": {
    "enabled": true,
    "embedding_model": "text-embedding-all-minilm-l6-v2-embedding",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "n_results": 3,
    "min_score": 0.1
  },
  "database": {
    "path": "data/chat_history.db",
    "max_connections": 5,
    "timeout": 30
  }
}
```

## File Processing

### Supported File Types

The application supports multiple file formats:

- **Text Files**: `.txt`, `.md`
- **Documents**: `.pdf`, `.docx`, `.doc`
- **Spreadsheets**: `.csv`, `.xlsx`
- **Code Files**: `.py`, `.js`, `.html`, etc.
- **Data Files**: `.json`, `.xml`

### Processing Pipeline

1. **File Upload**: User uploads file through Gradio interface
2. **Validation**: File type and size validation
3. **Text Extraction**: Extract text content from file
4. **Chunking**: Split text into manageable chunks
5. **Embedding**: Generate embeddings for chunks
6. **Storage**: Store in vector database
7. **Indexing**: Make content searchable

### File Processing Components

- **File Processor**: Core text extraction logic
- **Document Parsers**: Format-specific parsers
- **Text Cleaners**: Content preprocessing
- **Chunkers**: Text segmentation logic

## Error Handling and Monitoring

### Error Handling Strategy

The application implements a comprehensive error handling strategy:

1. **Service-Level Error Handling**
   - Retry mechanisms with exponential backoff
   - Graceful degradation
   - Fallback mechanisms

2. **Application-Level Error Handling**
   - User-friendly error messages
   - Error logging and monitoring
   - Error recovery mechanisms

3. **Infrastructure-Level Error Handling**
   - Network connectivity issues
   - Database connection problems
   - File system errors

### Monitoring and Health Checks

#### Service Health Monitoring
- **LLM Service**: API availability and response time
- **RAG Service**: Vector database connectivity and performance
- **Database Service**: Connection health and query performance

#### Performance Monitoring
- **Response Times**: Track API response times
- **Memory Usage**: Monitor memory consumption
- **CPU Usage**: Track CPU utilization
- **Error Rates**: Monitor error frequency and types

#### Health Check Endpoints
- Service availability checks
- Performance metrics collection
- Configuration validation
- Dependency status monitoring

## Dependencies and External Services

### Core Dependencies

#### LLM Integration
- **LM Studio**: Local LLM server
- **OpenAI Compatible API**: Standard API interface
- **Model Support**: Multiple model formats

#### Vector Database
- **ChromaDB**: Primary vector database
- **Embedding Models**: Multiple embedding model support
- **Index Management**: Vector index optimization

#### File Processing
- **PyPDF2**: PDF text extraction
- **python-docx**: Word document processing
- **pandas**: Spreadsheet data processing

### External Service Integration

#### GitHub Integration
- **GitHub API**: Repository management
- **Authentication**: Token-based authentication
- **Repository Operations**: Clone, push, pull operations

#### LM Studio Integration
- **Local Server**: Local LLM server management
- **Model Management**: Model loading and switching
- **API Compatibility**: OpenAI-compatible API

### Development Dependencies

#### Testing Framework
- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

#### Code Quality
- **ruff**: Code linting and formatting
- **mypy**: Type checking
- **black**: Code formatting

#### Development Tools
- **uv**: Package management
- **gradio**: Web interface framework
- **chromadb**: Vector database

## Development Workflow

### Code Organization

The codebase follows these organizational principles:

1. **Layered Architecture**: Clear separation between layers
2. **Dependency Injection**: Services injected where needed
3. **Configuration Management**: Centralized configuration
4. **Error Handling**: Consistent error handling patterns
5. **Testing**: Comprehensive test coverage

### Development Best Practices

1. **Code Style**: Follow PEP 8 and project-specific guidelines
2. **Type Hints**: Use type hints for better code documentation
3. **Documentation**: Document public APIs and complex logic
4. **Testing**: Write tests for all new functionality
5. **Error Handling**: Implement proper error handling and logging

### Testing Strategy

1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete user workflows
4. **Performance Tests**: Test application performance
5. **Error Handling Tests**: Test error scenarios

This structure provides a solid foundation for the SigmaHQ RAG application, with clear separation of concerns, comprehensive error handling, and extensible architecture for future enhancements.