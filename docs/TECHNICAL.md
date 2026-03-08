# Technical Documentation

## Architecture Overview

The SigmaHQ RAG Application follows a modular architecture with clear separation of concerns:

### Core Components

#### 1. **Models Layer** (`src/nicegui_app/models/`)
- **`chat_service.py`**: Manages conversation state, message history, and document processing
- **`data_service.py`**: Handles embedding generation and vector store operations
- **`rag_service.py`**: Implements Retrieval-Augmented Generation pipeline
- **`repository_service.py`**: Manages GitHub repository operations and indexing
- **`lm_studio_embeddings.py`**: Custom embedding wrapper for LM Studio API compatibility

#### 2. **Components Layer** (`src/nicegui_app/components/`)
- **`chat_message.py`**: Displays chat messages with typing indicators
- **`file_upload.py`**: Handles document uploads with drag-and-drop
- **`notification.py`**: Displays user notifications
- **`typing_indicator.py`**: Shows typing status during LLM responses

#### 3. **Pages Layer** (`src/nicegui_app/pages/`)
- **`chat_page.py`**: Main chat interface with document analysis
- **`github_repo_page.py`**: GitHub repository management interface
- **`logs_page.py`**: Application logging and monitoring

#### 4. **Services Layer**
- **`llm_service.py`**: LLM integration and prompt management
- **`document_processor.py`**: Multi-format document processing
- **`file_processor.py`**: File system operations and management
- **`logging_service.py`**: Application logging configuration

## Technology Stack

### Core Dependencies
- **NiceGUI 3.x**: Modern web framework for Python applications
- **LM Studio**: Local LLM and embedding model server
- **ChromaDB**: Vector database for semantic search
- **LangChain**: LLM orchestration and RAG pipeline management

### Document Processing
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX document processing
- **Pillow**: Image processing and OCR support
- **easyocr**: Optical Character Recognition for images

### Development Tools
- **uv**: Python package manager and virtual environment
- **pytest**: Testing framework
- **GitPython**: Git repository operations

## Data Flow

### Chat Interface Flow
1. **User Input**: Message sent via chat interface
2. **Document Processing**: Uploaded documents are processed and embedded
3. **Vector Search**: Relevant document chunks retrieved from ChromaDB
4. **RAG Generation**: LLM generates response with document context
5. **Response Display**: Answer displayed with source citations

### GitHub Repository Flow
1. **Repository Addition**: User adds GitHub repository URL and configuration
2. **Repository Cloning**: GitPython clones repository to local storage
3. **File Processing**: Target files are processed and embedded
4. **Vector Storage**: Document embeddings stored in ChromaDB
5. **Indexing**: Repository available for semantic search

## Configuration Management

### Configuration Files
- **`data/config.json`**: GitHub repository configurations
- **`pyproject.toml`**: Project dependencies and settings
- **`.env`**: Environment variables (optional)

### Configuration Structure
```json
{
  "github_repositories": [
    {
      "url": "https://github.com/user/repo",
      "branch": "main",
      "extensions": [".py", ".md", ".txt"],
      "enabled": true
    }
  ]
}
```

## Error Handling

### Retry Mechanisms
- **LM Studio Connection**: 3 attempts with exponential backoff
- **GitHub Operations**: Automatic retry for network issues
- **Vector Database**: Graceful degradation when unavailable

### Error Responses
- **Fallback Messages**: User-friendly error messages when services fail
- **Logging**: Comprehensive error logging for debugging
- **User Notifications**: Real-time error notifications in UI

## Performance Optimizations

### Caching Strategies
- **Embedding Cache**: Reuse embeddings for identical documents
- **Repository Cache**: Cache repository metadata and file lists
- **LLM Response Cache**: Cache frequent queries when appropriate

### Resource Management
- **Memory Management**: Efficient handling of large documents
- **Disk Space**: Automatic cleanup of temporary files
- **Network Usage**: Optimized API calls to LM Studio

## Security Considerations

### Local Processing
- **Privacy-First**: All processing occurs locally
- **No External APIs**: No data sent to external services
- **Secure Storage**: Configuration files stored locally

### Input Validation
- **URL Validation**: GitHub repository URL validation
- **File Type Restrictions**: Only allowed document formats
- **Size Limits**: Document size restrictions to prevent abuse

## Development Guidelines

### Code Organization
- **Modular Design**: Clear separation between UI, business logic, and data layers
- **Type Hints**: Comprehensive type annotations for better code quality
- **Documentation**: Inline documentation for complex logic

### Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Mock Services**: Mock external dependencies for testing

### Version Control
- **Git Workflow**: Feature branches and pull request workflow
- **Commit Standards**: Clear, descriptive commit messages
- **Changelog**: Comprehensive change tracking in `docs/CHANGELOG.md`

## Deployment Considerations

### Local Development
- **LM Studio Setup**: Required local LLM server configuration
- **Model Requirements**: Specific models needed for chat and embeddings
- **Port Configuration**: Default port 1234 for LM Studio

### Production Deployment
- **Resource Requirements**: Sufficient disk space for vector database
- **Model Management**: Proper model loading and management
- **Monitoring**: Application logging and performance monitoring

## Troubleshooting

### Common Issues
1. **LM Studio Not Running**: Ensure LM Studio is started and listening on port 1234
2. **Models Not Loaded**: Verify required models are loaded in LM Studio
3. **Connection Errors**: Check network connectivity and port availability
4. **Repository Cloning**: Verify GitHub URL format and network access

### Debug Information
- **Log Files**: Check `logs/` directory for detailed error information
- **Browser Console**: Check for JavaScript errors in browser console
- **LM Studio Logs**: Monitor LM Studio logs for model-related issues

## Future Enhancements

### Planned Features
- **Additional Document Formats**: Support for more file types
- **Advanced Search**: Enhanced search capabilities with filters
- **User Authentication**: Multi-user support with authentication
- **API Endpoints**: REST API for external integrations

### Performance Improvements
- **Parallel Processing**: Concurrent document processing
- **Smart Caching**: More intelligent caching strategies
- **Database Optimization**: Optimized vector database queries

This technical documentation provides a comprehensive overview of the SigmaHQ RAG Application's architecture, implementation details, and operational considerations.