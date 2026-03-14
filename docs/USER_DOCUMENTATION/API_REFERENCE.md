# SigmaHQ RAG - API Reference

This document provides comprehensive API reference for the SigmaHQ RAG application.

## Table of Contents
1. [REST API Endpoints](#rest-api-endpoints)
2. [Service Interfaces](#service-interfaces)
3. [Configuration](#configuration)
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
    "rag": "healthy"
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
      "uploaded_at": "2026-03-13T07:29:00Z"
    }
  ],
  "total": 1
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
    "max_tokens": 512
  },
  "rag": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "similarity_threshold": 0.1,
    "max_results": 3
  }
}
```

## Service Interfaces

### LLM Service (`src/core/llm_service.py`)
```python
class LLMService:
    def chat_completion(self, messages: List[Dict], **kwargs) -> ChatCompletion
    def completion(self, prompt: str, **kwargs) -> Completion
    def embedding(self, text: str) -> List[float]
    def stream_chat(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]
```

### RAG Service (`src/core/rag_service.py`)
```python
class RAGService:
    def add_document(self, file_path: str, metadata: Dict = None) -> str
    def query(self, question: str, top_k: int = 10) -> List[Dict]
    def get_relevant_documents(self, query: str, k: int) -> List[Document]
    def delete_document(self, doc_id: str) -> bool
    def generate_embeddings(self, texts: List[str]) -> np.ndarray
    def store_context(self, content: str, collection_name: str = None) -> None
    def retrieve_context(self, query: str, k: int = 3, min_score: float = 0.1) -> List[Dict]
```

### Chat Service (`src/models/rag_chat_service.py`)
```python
class RAGChatService:
    async def stream_response(
        self, 
        user_message: str,
        rag_enabled: bool = True,
        rag_n_results: int = 3,
        rag_min_score: float = 0.1,
        conversation_history_limit: int = 10
    ) -> AsyncGenerator[str, None]:
        """Stream RAG-enhanced response"""

    def cleanup(self) -> None:
        """Clean up resources"""
```

### Data Service (`src/models/data_service.py`)
```python
class DataService:
    def upload_document(self, file_path: str) -> Dict
    def list_documents(self, status: str = None) -> List[Dict]
    def delete_document(self, doc_id: str) -> bool
    def get_document_info(self, doc_id: str) -> Dict
```

### Config Service (`src/models/config_service.py`)
```python
class ConfigService:
    def load_config(self, config_path: str) -> Dict
    def validate_config(self) -> bool
    def get_config(self) -> Dict
    def save_config(self, config_path: str, config: Dict) -> bool
```

## Configuration

### Current Configuration File (`data/config.json`)
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
  },
  "ui_css": {
    "theme": "soft",
    "primary_color": "#4f46e5"
  }
}
```

### Environment Variables
```bash
# Network Configuration
PORT=8000
HOST=0.0.0.0

# LM Studio Configuration
OPENAI_API_KEY=lm-studio
OPENAI_BASE_URL=http://localhost:1234/v1

# Application Configuration
SIGMAHQ_ENV=production
PYTHONPATH=/path/to/sigmahqrag
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {},
    "timestamp": "2026-03-13T07:29:00Z"
  }
}
```

### Error Codes
- **VALIDATION_ERROR**: Input validation failed
- **NOT_FOUND**: Resource not found
- **INTERNAL_ERROR**: Internal server error
- **TIMEOUT_ERROR**: Request timeout
- **SERVICE_UNAVAILABLE**: Service temporarily unavailable

### Custom Exceptions (`src/shared/exceptions.py`)
```python
class ServiceError(Exception):
    """Base service exception"""

class ConfigurationError(ServiceError):
    """Configuration-related errors"""

class FileProcessingError(ServiceError):
    """File processing failures"""

class NetworkError(ServiceError):
    """Network connectivity issues"""

class LLMError(ServiceError):
    """LLM service errors"""

class RAGError(ServiceError):
    """RAG service errors"""
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
```

### Python Client Example
```python
from src.models.rag_chat_service import RAGChatService

# Initialize chat service
chat_service = RAGChatService(
    base_url="http://localhost:1234",
    rag_enabled=True,
    rag_n_results=3,
    rag_min_score=0.1
)

# Stream response
async for chunk in chat_service.stream_response("Hello"):
    print(chunk, end="", flush=True)
```

## Security

### CORS Configuration
```json
{
  "cors": {
    "enabled": true,
    "allowed_origins": ["*"],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE"]
  }
}