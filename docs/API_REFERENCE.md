# SigmaHQ RAG - API Reference

## Overview
This document provides comprehensive API reference for the SigmaHQ RAG application.

## Table of Contents
1. [REST API Endpoints](#rest-api-endpoints)
2. [Service Interfaces](#service-interfaces)
3. [Configuration API](#configuration-api)
4. [Error Handling](#error-handling)
5. [Examples](#examples)

## REST API Endpoints

### Health Check
```http
GET /health
```
**Description**: Check application health status
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-13T07:29:00Z",
  "services": {
    "database": "healthy",
    "llm": "healthy",
    "rag": "healthy",
    "lm_studio": "healthy"
  }
}
```

### Chat Endpoints

#### Send Message
```http
POST /api/chat/send
Content-Type: application/json

{
  "message": "Your question here",
  "session_id": "optional-session-id"
}
```
**Response**:
```json
{
  "response": "AI response text",
  "session_id": "session-id",
  "references": [
    {
      "document": "document-name.pdf",
      "page": 1,
      "content": "relevant content excerpt"
    }
  ],
  "metadata": {
    "response_time": 2.5,
    "model_used": "mistralai/ministral-3-14b-reasoning"
  }
}
```

#### Get Chat History
```http
GET /api/chat/history?session_id=your-session-id&limit=50
```
**Response**:
```json
{
  "session_id": "session-id",
  "messages": [
    {
      "role": "user",
      "content": "User message",
      "timestamp": "2026-03-13T07:29:00Z"
    },
    {
      "role": "assistant",
      "content": "Assistant response",
      "timestamp": "2026-03-13T07:29:02Z",
      "references": [...]
    }
  ]
}
```

#### Clear Chat History
```http
DELETE /api/chat/history?session_id=your-session-id
```
**Response**:
```json
{
  "success": true,
  "message": "Chat history cleared"
}
```

### Document Endpoints

#### Upload Document
```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: [binary file data]
```
**Response**:
```json
{
  "success": true,
  "document_id": "doc-123",
  "filename": "document.pdf",
  "status": "processing",
  "size": 1024000
}
```

#### List Documents
```http
GET /api/documents?status=completed&limit=100
```
**Response**:
```json
{
  "documents": [
    {
      "id": "doc-123",
      "filename": "document.pdf",
      "status": "completed",
      "size": 1024000,
      "uploaded_at": "2026-03-13T07:29:00Z",
      "chunks": 150
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 100
}
```

#### Delete Document
```http
DELETE /api/documents/doc-123
```
**Response**:
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

#### Get Document Details
```http
GET /api/documents/doc-123
```
**Response**:
```json
{
  "id": "doc-123",
  "filename": "document.pdf",
  "status": "completed",
  "size": 1024000,
  "uploaded_at": "2026-03-13T07:29:00Z",
  "chunks": 150,
  "metadata": {
    "pages": 10,
    "language": "en",
    "content_type": "text"
  }
}
```

### Configuration Endpoints

#### Get Configuration
```http
GET /api/config
```
**Response**:
```json
{
  "llm": {
    "base_url": "http://localhost:1234/v1",
    "model": "mistralai/ministral-3-14b-reasoning",
    "temperature": 0.7,
    "max_tokens": 2048
  },
  "rag": {
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "similarity_threshold": 0.7,
    "max_results": 10
  },
  "performance": {
    "memory_limit_mb": 2048,
    "max_concurrent_requests": 10,
    "cache_ttl": 3600
  }
}
```

#### Update Configuration
```http
PUT /api/config
Content-Type: application/json

{
  "rag": {
    "chunk_size": 1500,
    "similarity_threshold": 0.8
  }
}
```
**Response**:
```json
{
  "success": true,
  "message": "Configuration updated successfully"
}
```

### System Endpoints

#### Get System Status
```http
GET /api/system/status
```
**Response**:
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "disk_usage": 23.4,
  "active_sessions": 5,
  "total_documents": 150,
  "uptime": "2h 15m 30s"
}
```

#### Get Logs
```http
GET /api/logs?level=INFO&limit=100&start_time=2026-03-13T07:00:00Z
```
**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2026-03-13T07:29:00Z",
      "level": "INFO",
      "message": "Application started successfully",
      "source": "main"
    }
  ],
  "total": 100,
  "filtered": 50
}
```

## Service Interfaces

### LLM Service
```python
class LLMService:
    def chat_completion(self, messages: List[Dict], **kwargs) -> str
    def completion(self, prompt: str, **kwargs) -> str
    def embedding(self, text: str) -> List[float]
    def stream_chat(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]
```

### RAG Service
```python
class RAGService:
    def add_document(self, file_path: str, metadata: Dict = None) -> str
    def query(self, question: str, top_k: int = 10) -> List[Dict]
    def get_relevant_documents(self, query: str, k: int) -> List[Document]
    def delete_document(self, doc_id: str) -> bool
```

### Chat Service
```python
class ChatService:
    def chat(self, message: str, session_id: str = None) -> Dict
    def get_session_history(self, session_id: str) -> List[Dict]
    def clear_session(self, session_id: str) -> bool
    def export_chat(self, session_id: str) -> str
```

### Data Service
```python
class DataService:
    def upload_document(self, file_path: str) -> Dict
    def list_documents(self, status: str = None) -> List[Dict]
    def delete_document(self, doc_id: str) -> bool
    def get_document_info(self, doc_id: str) -> Dict
```

## Configuration API

### Environment Variables
```bash
# LM Studio Configuration
OPENAI_API_KEY=lm-studio
OPENAI_BASE_URL=http://localhost:1234/v1

# Application Configuration
SIGMAHQ_ENV=production
PYTHONPATH=/path/to/sigmahqrag

# Database Configuration
DATABASE_URL=sqlite:///data/sigmahq.db
```

### Configuration File Structure
```json
{
  "llm": {
    "base_url": "http://localhost:1234/v1",
    "api_key": "lm-studio",
    "model": "mistralai/ministral-3-14b-reasoning",
    "embedding_model": "text-embedding-all-minilm-l6-v2-embedding",
    "timeout": 60,
    "retries": 3
  },
  "rag": {
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "similarity_threshold": 0.7,
    "max_results": 10,
    "collection_name": "documents"
  },
  "database": {
    "url": "sqlite:///data/sigmahq.db",
    "timeout": 30,
    "pool_size": 10,
    "max_overflow": 20
  },
  "performance": {
    "memory_limit_mb": 2048,
    "max_concurrent_requests": 10,
    "cache_ttl": 3600,
    "enable_caching": true
  }
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "message",
      "reason": "Field is required"
    },
    "timestamp": "2026-03-13T07:29:00Z"
  }
}
```

### Error Codes
- **VALIDATION_ERROR**: Input validation failed
- **NOT_FOUND**: Resource not found
- **INTERNAL_ERROR**: Internal server error
- **TIMEOUT_ERROR**: Request timeout
- **RATE_LIMIT_ERROR**: Rate limit exceeded
- **AUTH_ERROR**: Authentication failed
- **SERVICE_UNAVAILABLE**: Service temporarily unavailable

### Error Handling Examples
```python
try:
    response = rag_service.query("your question")
except ValidationError as e:
    # Handle validation errors
    print(f"Validation failed: {e}")
except ServiceError as e:
    # Handle service errors
    print(f"Service error: {e}")
except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

## Examples

### Basic Chat Example
```python
import requests

# Send a chat message
response = requests.post('http://localhost:8000/api/chat/send', json={
    'message': 'What is the capital of France?',
    'session_id': 'session-123'
})

result = response.json()
print(f"Response: {result['response']}")
print(f"References: {result['references']}")
```

### Document Upload Example
```python
import requests

# Upload a document
with open('document.pdf', 'rb') as f:
    files = {'file': ('document.pdf', f, 'application/pdf')}
    response = requests.post('http://localhost:8000/api/documents/upload', files=files)

result = response.json()
print(f"Document ID: {result['document_id']}")
print(f"Status: {result['status']}")
```

### Configuration Update Example
```python
import requests

# Update RAG configuration
response = requests.put('http://localhost:8000/api/config', json={
    'rag': {
        'chunk_size': 1500,
        'similarity_threshold': 0.8
    }
})

result = response.json()
print(f"Success: {result['success']}")
```

### System Monitoring Example
```python
import requests

# Get system status
response = requests.get('http://localhost:8000/api/system/status')
status = response.json()

print(f"CPU Usage: {status['cpu_usage']}%")
print(f"Memory Usage: {status['memory_usage']}%")
print(f"Active Sessions: {status['active_sessions']}")
```

## WebSocket Support

### Chat Streaming
```javascript
const socket = new WebSocket('ws://localhost:8000/ws/chat');

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'chunk') {
        // Handle streaming response chunk
        console.log('Response chunk:', data.content);
    } else if (data.type === 'complete') {
        // Handle complete response
        console.log('Complete response:', data.content);
    }
};

// Send message
socket.send(JSON.stringify({
    type: 'message',
    content: 'Your question here',
    session_id: 'session-123'
}));
```

## Rate Limiting

### Rate Limit Headers
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1647123456
```

### Rate Limit Configuration
```json
{
  "rate_limit": {
    "enabled": true,
    "requests_per_minute": 100,
    "burst_size": 10
  }
}
```

## Security

### Authentication
Currently, the API uses basic authentication. For production deployments:
- Use HTTPS for all API calls
- Implement API key authentication
- Use OAuth2 for user authentication
- Enable CORS restrictions

### CORS Configuration
```json
{
  "cors": {
    "enabled": true,
    "allowed_origins": ["https://your-domain.com"],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
    "allowed_headers": ["Content-Type", "Authorization"]
  }
}
```

This API reference provides comprehensive documentation for integrating with the SigmaHQ RAG application programmatically.