# SigmaHQ Chat Interface

A comprehensive chat interface for document analysis powered by Retrieval-Augmented Generation (RAG) with local embeddings. This system allows users to upload documents (PDF, TXT, DOCX, images) and ask questions about their content.

## TODO LIST

Very WIP 

- [ ] GitHub Repository Management 
  - [x] fix github update
  - [ ] fix Add repository
  - [ ] Fix Actions
  - [ ] Fix other errors I don't event kown 
- [ ] chromadb
- [ ] Chat

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
  │   │   └── github_repo_page.py      # GitHub repository management page
  │   ├── app.py                      # NiceGUI application setup
  │   └── __init__.py
  └── __init__.py
config/
  ├── sigmahqllm.json
  └── github.json
```

## Features
- **Multi-modal chat interface**: Support for text, documents (PDF, TXT, DOCX), and images
- **Local embeddings**: Generate embeddings using SentenceTransformers without remote calls
- **Document analysis**: Extract text from uploaded documents and answer questions about content
- **Conversation history**: Maintain context across multiple messages
- **Responsive UI**: Modern, user-friendly interface built with NiceGUI 3.x
- **Drag-and-drop uploads**: Easy document uploading experience
- **Real-time updates**: Typing indicators and instant message display
- **GitHub Repository Management**: Add, edit, and manage GitHub repositories for indexing and analysis

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
1. Open the chat interface in your browser at `http://localhost:8000`
2. Upload documents using drag-and-drop or file selector
3. Ask questions about the uploaded document content
4. View responses with context from your documents
5. Clear chat history as needed
6. Manage GitHub repositories by navigating to `/github-repo`:
   - Add new repositories for indexing
   - Enable/disable repositories using the toggle switch
   - Update all enabled repositories at once
   - Remove repositories no longer needed

## GitHub Repository Management
The application includes a dedicated page for managing GitHub repositories that can be indexed and analyzed:

- **Add Repositories**: Enter the repository URL, branch name, and file extensions to include (uses `add_box` icon)
- **Enable/Disable**: Use the toggle switch to enable or disable repositories
- **Update All**: Update all enabled repositories at once (uses `source` icon)
- **Add/Edit/Delete**: Add new repositories, edit existing ones, or delete them permanently (uses `edit_document` for edit, `delete_outline` for delete)
- **Reactive UI**: The page is centered and responsive, built with NiceGUI 3.x components
- **Background Updates**: Repository updates run in the background without freezing the page

All repository configurations are stored in `config/github.json`.

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