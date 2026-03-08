# Environment Instructions

## Project Context
This is the **SigmaHQ RAG Application** - a Retrieval-Augmented Generation system with document analysis powered by LM Studio. The application features:
- Multi-modal chat interface with document upload (PDF, TXT, DOCX, images)
- LM Studio integration for local LLM and embedding generation
- GitHub repository management for indexing and analysis
- Vector database (ChromaDB) for semantic search
- NiceGUI 3.x for the web interface

## Documentation
- Use the documentation:
  - [NiceGUI 3.x](https://nicegui.io/documentation) - UI framework
  - [LM Studio](https://lmstudio.ai/) - Local LLM server setup
  - [ChromaDB](https://www.trychroma.com) - Vector database
  - [LangChain](https://python.langchain.com) - RAG framework
  - [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma) - Sigma rule parsing
  - [Material Icons](https://fonts.google.com/icons?icon.set=Material+Icons) - UI icons

## Python Environment
- Always use the `uv` Python environment and package manager for Python:
  - `uv sync` to install all dependencies from pyproject.toml
  - `uv run ...` to execute a Python script
  - `uvx ...` to run a program directly from PyPI
  - `uv add ...` to add or manage packages, dependencies, etc.
  - `uv run pytest` to run tests
  - `uvx black .` to format code
  - `uvx ruff check .` to lint code
  - `uvx pyflakes` to find unused import

## NiceGUI 3.x
- Use the latest NiceGUI 3.x for building UIs:
  - Install with: `uv add nicegui`
  - Follow [NiceGUI documentation](https://nicegui.io/documentation) for component usage and best practices
  - Ensure compatibility with other dependencies (e.g., AG Grid)
  - Use components from `src/nicegui_app/components/` for consistent UI patterns

## LM Studio Integration
- **Required Models**: Ensure these models are loaded in LM Studio:
  - `mistralai/ministral-3-14b-reasoning` - Chat model for responses
  - `text-embedding-all-minilm-l6-v2-embedding` - Embedding model for RAG
- **Server Configuration**:
  - LM Studio must be running at `http://localhost:1234`
  - Use the custom `LMStudioEmbeddings` class for optimal API compatibility
  - All LLM operations use OpenAI-compatible endpoints
- **Error Handling**: The application includes retry logic with 3 attempts and exponential backoff when connecting to LM Studio

## RAG and Vector Database
- **ChromaDB**: Vector database for semantic search and document retrieval
  - Data stored in `.chromadb/` directory
  - Use `uv run python -m chromadb` for database operations if needed
- **Document Processing**:
  - PDF files processed with PyPDF2
  - DOCX files processed with python-docx
  - Images processed with Pillow and easyocr for OCR
  - Text extraction supports multiple formats
- **Embedding Generation**: Custom `LMStudioEmbeddings` class handles all embedding operations

## Code Structure and Patterns
- **Modular Architecture**: Follow the existing component/service pattern
  - Components: `src/nicegui_app/components/` - UI elements
  - Models: `src/nicegui_app/models/` - Business logic and services
  - Pages: `src/nicegui_app/pages/` - Main application pages
- **Error Handling**: Implement robust error handling with fallback responses
- **Streaming**: Use async generators for streaming LLM responses
- **Configuration**: Store application settings in `data/config.json`

## ast-grep
You are operating in an environment where `ast-grep` is installed.
For code searches requiring syntax or structure understanding, use:
```bash
ast-grep --lang [language] -p '<pattern>'
```
Adjust the --lang flag for the specific language. Avoid text-only search tools unless explicitly requested.

## Git Policy

Never perform Git commits, pushes, or any version control operations.
If changes need to be saved or versioned, notify the user and request explicit instructions.

## Logging System Requirements

When implementing logging functionality:

1. **Use Centralized Logging Service**: Always use the logging service from `src/nicegui_app.models.logging_service`
2. **Get Logger Instance**: Use `get_logger(__name__)` for consistent logger naming
3. **Log Levels**: Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
4. **Log Rotation**: The system automatically handles log rotation at 10MB with 5 backup files
5. **Real-time Monitoring**: The Logs page provides live tail-like functionality for monitoring logs
6. **Page Height for Logs**: The Logs page uses `h-[60vh]` for the log display area to accommodate the log viewer interface

## File Handling Guidelines

- **Configuration Files**: 
  - `data/config.json` - GitHub repository configurations
  - `pyproject.toml` - Python dependencies and project metadata
  - `uv.lock` - Locked dependency versions
- **Data Storage**:
  - `.chromadb/` - Vector database storage (do not modify manually)
  - `data/github/` - GitHub repository data
  - `data/local/` - Local document processing data
  - `logs/` - Application log files (created automatically)
- **Application Files**:
  - `src/nicegui_app/` - Main application code
  - `tests/` - Test files
  - `docs/` - Documentation
- **File Encoding**: Always use UTF-8 with LF line endings for files
- **Dependencies**: Use `uv sync` to ensure consistent dependency versions across environments
