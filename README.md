# SigmaHQ Chat Interface

A comprehensive chat interface for document analysis powered by Retrieval-Augmented Generation (RAG) with local embeddings. This system allows users to upload documents (PDF, TXT, DOCX, images) and ask questions about their content.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [GitHub Repository Management](#github-repository-management)
- [Development](#development)
- [Code Review Findings](#code-review-findings)
- [Contributing](#contributing)

## Features

- **Multi-modal chat interface**: Support for text, documents (PDF, TXT, DOCX), and images
- **Local embeddings**: Generate embeddings using Ollama without remote calls
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
   uv pip install -r requirements.txt
   ```

3. Ensure Ollama is installed and running:
   ```bash
   ollama serve
   ```

4. Pull the required embedding model:
   ```bash
   ollama pull all-minilm
   ```

5. Run the application:
   ```bash
   uv run python main.py
   ```

6. Access the chat interface at `http://localhost:8000`

## Prerequisites

- **Ollama**: Local LLM and embedding model server
  - Install from [ollama.com](https://ollama.com)
  - Ensure it's running at `http://127.0.0.1:1234`
  - Pull the embedding model: `ollama pull all-minilm`

- **Python**: Version specified in `.python-version` file

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

All repository configurations are stored in `config/github.json`.

## GitHub Repository Management

The application includes a dedicated page for managing GitHub repositories that can be indexed and analyzed:

### Key Features:
- **Local embeddings**: All embeddings are generated using the Ollama server running at `http://127.0.0.1:1234`
- **No external API calls**: Everything runs locally for privacy and performance
- **RAG pipeline**: Document context is stored in a vector database (ChromaDB) and retrieved based on semantic similarity
- **Error handling**: Automatic retry mechanism with fallback responses if the Ollama server is unavailable
- **Retry logic**: 3 attempts with exponential backoff when connecting to Ollama server

### Repository Configuration:
- **URL**: GitHub repository URL (e.g., `https://github.com/user/repo`)
- **Branch**: Git branch to clone (default: `main`)
- **Extensions**: File extensions to include (e.g., `.py,.md,.txt`)
- **Enabled**: Toggle to enable/disable repository indexing

### Requirements:
- Ollama server running locally at `http://127.0.0.1:1234`
- Embedding model pulled (`all-minilm` recommended)
- Sufficient disk space for vector database storage (stored in `.chromadb/` directory)

### Troubleshooting:
- **Ollama server not running**: Start the server with `ollama serve` and ensure it's listening on port 1234
- **Model not found**: Pull the required model with `ollama pull all-minilm`
- **Connection errors**: Check that no other service is using port 1234 or restart the Ollama server

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
- **Ollama**: Local LLM and embedding model server
- **ChromaDB**: Vector database for RAG
- **PyPDF2**: PDF document processing
- **python-docx**: DOCX document processing
- **Pillow**: Image processing
- **easyocr**: OCR for image text extraction
- **PySigma**: Sigma rule parsing (optional)
- **GitPython**: GitHub repository operations (optional)
- **AG Grid**: Data grid for GitHub repository management

### Code Review Findings

A comprehensive code review has been performed on the project. Key findings include:

**Dead Code:**
- `card.py`: Functionally incomplete card component
- `notification.py`: Missing task tracking
- `chat_service.py`: Unused serialization methods
- `data_service.py`: Placeholder stub methods
- `github_repo_page.py`: Unimplemented handler functions
- `chat_service.py`: Console-only methods

**Optimization Opportunities:**
- UI rendering issues in chat message components
- Redundant file handling code
- Incorrect event handling
- Overly complex scrolling implementation
- Consolidate redundant null/attribute checks

**Code Quality Issues:**
- Mock responses instead of real LLM integration
- Collision-prone ID generation
- Hardcoded retry parameters
- Missing GitHub API rate limiting

**Missing Features:**
- No actual LLM integration
- Poor file upload error handling
- Typing indicators not implemented
- No conversation persistence
- No export/import functionality
- Missing temporary file cleanup

See `TODO.md` for the detailed action items and prioritized task list.

## Contributing

Contributions are welcome! Please review the code review findings in `TODO.md` and submit pull requests for any improvements.

### Areas for Contribution:
- Implement actual LLM integration
- Add comprehensive test coverage
- Improve UI components
- Enhance error handling
- Add new features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [NiceGUI](https://nicegui.io) - UI Framework
- [Ollama](https://ollama.com) - Local LLM and embedding models
- [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma) - Sigma rule parsing
- [ChromaDB](https://www.trychroma.com) - Vector database
