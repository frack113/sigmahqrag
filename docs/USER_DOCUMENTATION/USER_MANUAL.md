# SigmaHQ RAG - User Manual

This user manual provides comprehensive guidance for using the SigmaHQ RAG Gradio application.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Chat Interface](#chat-interface)
3. [Data Management](#data-management)
4. [Configuration](#configuration)
5. [GitHub Integration](#github-integration)
6. [Logs Viewer](#logs-viewer)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Access to the SigmaHQ RAG application at `http://localhost:8000`

### Initial Setup
1. **Start the application**: `uv run python main.py`
2. **Access the Application**: Open your browser and navigate to `http://localhost:8000`
3. **Verify Connection**: Check that all components load properly
4. **Test Chat**: Send a simple test message

### Interface Overview
The application is organized into tabs:
- **RAG Chat**: Main chat interface for asking questions
- **Data**: Document management and upload
- **GitHub**: GitHub repository integration
- **Files**: File system management
- **Config**: System settings and configuration
- **Logs**: Application monitoring

## Chat Interface

### Starting a Conversation
1. Type your question in the chat input box
2. Press Enter or click "Send"
3. View the AI's response with context from your documents

### RAG Settings
Adjust RAG behavior via the "RAG Settings" accordion:
- **Enable RAG**: Toggle RAG functionality on/off
- **History Limit**: Control how many previous messages to consider (default: 10)
- **RAG Results**: Number of relevant documents to retrieve (default: 3)
- **Min Score**: Minimum similarity score threshold (default: 0.1)

### Chat Features
- **Streaming Responses**: Real-time response generation
- **Session Persistence**: Conversation history is maintained during the session
- **Context Awareness**: AI remembers previous messages

### Commands
Type these commands to access features:
- `/help` - Show available commands
- `/stats` - Display system statistics
- `/clear` - Clear chat history
- `/export` - Export chat to JSON file

## Data Management

### Document Upload
1. Navigate to the "Data" tab
2. Drag and drop files or use the file browser
3. Monitor processing progress
4. Documents are automatically indexed for search

### Supported File Types
The application supports various document formats:
- **Text**: `.txt`, `.md`
- **Documents**: PDF, DOCX
- **Code**: Python, JavaScript, HTML, etc.

## Configuration

### Accessing Settings
Navigate to the "Config" tab to adjust system settings.

### Network Configuration
- **IP Address**: Set the network interface (default: 127.0.0.1)
- **Port**: HTTP server port (default: 8000)
- **Timeout**: Request timeout in seconds (default: 30)

### LLM Settings
- **Model**: Selected language model
- **Temperature**: Creativity control (0.7 default)
- **Max Tokens**: Maximum response length
- **Base URL**: LM Studio server address

### UI Settings
- **Theme**: Soft theme applied globally
- **Colors**: Primary (#4f46e5), Secondary (#10b981)

## GitHub Integration

### Repository Management
Navigate to the "GitHub" tab to:
- View connected repositories
- Pull latest content from specified branches
- Manage repository integrations

### Configuration
Edit `data/config.json` to configure GitHub repositories for knowledge base integration.

## Logs Viewer

### Viewing Logs
Navigate to the "Logs" tab to see real-time application logs:
- **Info**: General system messages
- **Warning**: Non-critical issues
- **Error**: Errors requiring attention
- **Debug**: Detailed debugging information

### Log Filtering
- Filter by log level
- Search for specific messages
- Export logs for analysis

## Configuration File

### Editing `data/config.json`
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
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000,
    "base_url": "http://127.0.0.1:1234"
  }
}
```

## Troubleshooting

### Chat Not Responding
**Symptoms**: No response or very slow response
**Solutions**:
1. Check if LM Studio is running on port 1234
2. Verify network configuration in Config tab
3. Check logs for error messages

### Connection Errors
**Cause**: Cannot connect to LM Studio server
**Solution**:
1. Start LM Studio application
2. Verify server is running on configured port
3. Check base_url configuration

### Slow Performance
**Solutions**:
1. Check system resources (CPU, memory)
2. Reduce conversation history limit
3. Adjust RAG results count
4. Consider model optimizations

## Best Practices

### Document Management
- Use descriptive file names
- Organize documents logically
- Regularly remove unused documents

### Chat Usage
- Ask specific, well-formulated questions
- Use follow-up questions for deeper exploration
- Export important conversations

### System Maintenance
- Monitor logs regularly
- Keep application updated
- Backup configuration settings

## Architecture Overview

The SigmaHQ RAG application follows a layered architecture:

```
Presentation Layer (Gradio UI)
    ↓
Application Layer (SigmaHQApplication)
    ↓
Core Services (LLM, RAG, Chat)
    ↓
Infrastructure (Database, File System, LM Studio)
    ↓
Shared Utilities (Config, Utils, Exceptions)
```

## Support

For additional support:
- Check the logs tab for error details
- Review configuration in `data/config.json`
- Consult the API reference for integration help