# SigmaHQ Multi-Modal Chat Interface

A comprehensive chat interface for document analysis powered by Retrieval-Augmented Generation (RAG) with local embeddings. This system allows users to upload documents (PDF, TXT, DOCX, images) and ask questions about their content.

## Project Structure
```
src/
  ├── nicegui_app/
  │   ├── components/
  │   │   ├── card.py
  │   │   ├── chat_message.py          # Chat message display component
  │   │   ├── file_upload.py           # Document upload with drag-and-drop
  │   │   └── notification.py
  │   ├── models/
  │   │   ├── chat_service.py         # Conversation state and document processing
  │   │   └── data_service.py          # Embedding generation and vector store
  │   ├── pages/
  │   │   ├── chat_page.py            # Main chat interface
  │   │   └── dashboard.py
  │   ├── app.py                      # NiceGUI application setup
  │   └── __init__.py
  └── __init__.py
config/
  ├── sigmahqllm.json
  └── github.yml
```

## Features
- **Multi-modal chat interface**: Support for text, documents (PDF, TXT, DOCX), and images
- **Local embeddings**: Generate embeddings using SentenceTransformers without remote calls
- **Document analysis**: Extract text from uploaded documents and answer questions about content
- **Conversation history**: Maintain context across multiple messages
- **Responsive UI**: Modern, user-friendly interface built with NiceGUI 3.x
- **Drag-and-drop uploads**: Easy document uploading experience
- **Real-time updates**: Typing indicators and instant message display

## Installation
1. Clone this repository.
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
- Ensure you have Ollama installed and running locally at `http://127.0.0.1:1234`
- Pull the required embedding model (e.g., `all-minilm`) using the Ollama CLI:
  ```bash
  ollama pull all-minilm
  ```

## Usage
1. Open the chat interface in your browser
2. Upload documents using drag-and-drop or file selector
3. Ask questions about the uploaded document content
4. View responses with context from your documents
5. Clear chat history as needed

## RAG with ollama-python
This application uses `ollama-python` for local embedding generation and Retrieval-Augmented Generation (RAG).

### Key Features:
- **Local embeddings**: All embeddings are generated using the Ollama server running at `http://127.0.0.1:1234`
- **No external API calls**: Everything runs locally for privacy and performance
- **RAG pipeline**: Document context is stored in a vector database (ChromaDB) and retrieved based on semantic similarity
- **Error handling**: Automatic retry mechanism with fallback responses if the Ollama server is unavailable
- **Retry logic**: 3 attempts with exponential backoff when connecting to Ollama server

### Requirements:
- Ollama server running locally at `http://127.0.0.1:1234`
- Embedding model pulled (`all-minilm` recommended)
- Sufficient disk space for vector database storage (stored in `.chromadb/` directory)

### Troubleshooting:
- **Ollama server not running**: Start the server with `ollama serve` and ensure it's listening on port 1234
- **Model not found**: Pull the required model with `ollama pull all-minilm`
- **Connection errors**: Check that no other service is using port 1234 or restart the Ollama server

## Development
The project follows a modular architecture:
- **Components**: UI elements like chat messages and file uploaders
- **Models**: Business logic for chat processing and data services  
- **Pages**: Main application pages with routing
- **Services**: Core functionality for embeddings, RAG, and conversation management