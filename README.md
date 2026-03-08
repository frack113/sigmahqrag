# SigmaHQ RAG Application

A comprehensive Retrieval-Augmented Generation (RAG) application with document analysis powered by LM Studio. This system allows users to upload documents (PDF, TXT, DOCX, images) and ask questions about their content.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [GitHub Repository Management](#github-repository-management)
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)

## Features

- **Multi-modal chat interface**: Support for text, documents (PDF, TXT, DOCX), and images
- **LM Studio Integration**: Generate embeddings using LM Studio with custom API compatibility
- **Document analysis**: Extract text from uploaded documents and answer questions about content
- **Conversation history**: Maintain context across multiple messages
- **Responsive UI**: Modern, user-friendly interface built with NiceGUI 3.x
- **Drag-and-drop uploads**: Easy document uploading experience
- **Real-time updates**: Typing indicators and instant message display
- **GitHub Repository Management**: Add, edit, and manage GitHub repositories for indexing and analysis
- **Vector database**: Semantic search using ChromaDB for document retrieval
- **Privacy-focused**: All processing runs locally on your machine

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/frack113/sigmahqrag.git
   cd sigmahqrag
   ```

2. Install dependencies using uv (recommended):
   ```bash
   uv sync
   ```

3. Ensure LM Studio is installed and running:
   - Download from [LM Studio](https://lmstudio.ai/)
   - Load the following models:
     - `mistralai/ministral-3-14b-reasoning` (chat model)
     - `text-embedding-all-minilm-l6-v2-embedding` (embedding model)
   - Start server on port 1234

4. Run the application:
   ```bash
   uv run python main.py
   ```

5. Access the chat interface at `http://localhost:8000`

## Prerequisites

- **LM Studio**: Local LLM and embedding model server
  - Install from [LM Studio](https://lmstudio.ai/)
  - Load required models:
    - `mistralai/ministral-3-14b-reasoning` for chat
    - `text-embedding-all-minilm-l6-v2-embedding` for embeddings
  - Ensure it's running at `http://localhost:1234`

- **Python**: Version 3.10 or higher

- **Disk space**: Sufficient space for vector database storage (`.chromadb/` directory)

## Usage

### Basic Chat

1. Open the chat interface in your browser at `http://localhost:8000`
2. Upload documents using drag-and-drop or file selector
3. Ask questions about the uploaded document content
4. View responses with context from your documents
5. Clear chat history as needed

### GitHub Repository Management

Navigate to `/github-repo` to manage GitHub repositories:

- **Add Repositories**: Enter the repository URL, branch name, and file extensions to include
- **Enable/Disable**: Use the toggle switch to enable or disable repositories
- **Update All**: Update all enabled repositories at once
- **Add/Edit/Delete**: Add new repositories, edit existing ones, or delete them permanently
- **Save Changes**: Click the Save button to persist your configuration

All repository configurations are stored in `data/config.json`.

## GitHub Repository Management

The application includes a dedicated page for managing GitHub repositories that can be indexed and analyzed:

### Key Features:
- **LM Studio Integration**: All embeddings are generated using the LM Studio server running at `http://localhost:1234`
- **Custom Embeddings**: Uses custom `LMStudioEmbeddings` class for optimal API compatibility
- **RAG pipeline**: Document context is stored in a vector database (ChromaDB) and retrieved based on semantic similarity
- **Error handling**: Automatic retry mechanism with fallback responses if the LM Studio server is unavailable
- **Retry logic**: 3 attempts with exponential backoff when connecting to LM Studio server

### Repository Configuration:
- **URL**: GitHub repository URL (e.g., `https://github.com/user/repo`)
- **Branch**: Git branch to clone (default: `main`)
- **Extensions**: File extensions to include (e.g., `.py,.md,.txt`)
- **Enabled**: Toggle to enable/disable repository indexing

### Requirements:
- LM Studio server running locally at `http://localhost:1234`
- Required models loaded in LM Studio
- Sufficient disk space for vector database storage (stored in `.chromadb/` directory)

### Troubleshooting:
- **LM Studio server not running**: Start LM Studio and ensure it's listening on port 1234
- **Models not found**: Load the required models in LM Studio
- **Connection errors**: Check that no other service is using port 1234 or restart LM Studio

## Development

### Project Architecture

The project follows a modular architecture:

- **Components**: UI elements like chat messages and file uploaders
  - `card.py`: Card component (currently incomplete)
  - `chat_message.py`: Chat message display component
  - `file_upload.py`: Document upload with drag-and-drop
  - `notification.py`: Notification component

- **Models**: Business logic for chat processing and data services
  - `chat_service.py`: Conversation state and document processing
  - `data_service.py`: Embedding generation and vector store
  - `rag_service.py`: Retrieval-Augmented Generation operations
  - `repository_service.py`: GitHub repository operations

- **Pages**: Main application pages with routing
  - `chat_page.py`: Main chat interface
  - `github_repo_page.py`: GitHub repository management page

- **Services**: Core functionality for embeddings, RAG, and conversation management

### Dependencies

The project uses the following main dependencies:

- **NiceGUI 3.x**: UI framework
- **LM Studio**: Local LLM and embedding model server
- **ChromaDB**: Vector database for RAG
- **PyPDF2**: PDF document processing
- **python-docx**: DOCX document processing
- **Pillow**: Image processing
- **easyocr**: OCR for image text extraction
- **PySigma**: Sigma rule parsing (optional)
- **GitPython**: GitHub repository operations (optional)
- **AG Grid**: Data grid for GitHub repository management

### Key Optimizations

- **Custom Embeddings**: Created `LMStudioEmbeddings` class for perfect LM Studio API compatibility
- **Clean Dependencies**: Removed all Ollama dependencies, using only OpenAI-compatible endpoints
- **Optimized Imports**: Removed all unused imports and dependencies
- **Single Test File**: Consolidated testing into one comprehensive test file
- **Production Ready**: Clean, documented, and fully tested codebase

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[LM Studio Setup Guide](docs/LM_STUDIO_SETUP_GUIDE.md)**: Complete setup instructions for LM Studio
- **[UV Setup Summary](docs/UV_SETUP_SUMMARY.md)**: Python environment and dependency management
- **[Project Summary](docs/PROJECT_SUMMARY.md)**: Complete project overview and technical details
- **[Optimization Summary](docs/OPTIMIZATION_SUMMARY.md)**: Code optimization and cleanup details
- **[AGENTS.md](docs/AGENTS.md)**: AI agent configuration and usage

## Contributing

Contributions are welcome! The project is now optimized and production-ready.

### Areas for Contribution:
- Implement additional UI components
- Add comprehensive test coverage
- Enhance error handling
- Add new features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [NiceGUI](https://nicegui.io) - UI Framework
- [LM Studio](https://lmstudio.ai) - Local LLM and embedding models
- [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma) - Sigma rule parsing
- [ChromaDB](https://www.trychroma.com) - Vector database