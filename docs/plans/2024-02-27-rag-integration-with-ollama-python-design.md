# RAG Integration with ollama-python

## Overview
This design document outlines the integration of `ollama-python` for Retrieval-Augmented Generation (RAG) and embeddings in the SigmaHQ Multi-Modal Chat Interface. The goal is to replace the current embedding logic using SentenceTransformers with `ollama-python`, leveraging its optimized capabilities for local embeddings and RAG.

## Project Context
- **Current State**: The project uses SentenceTransformers for generating embeddings locally. It supports multi-modal chat interfaces (text, documents, images) and provides a responsive UI built with NiceGUI 3.x.
- **Objective**: Integrate `ollama-python` to generate embeddings and perform RAG using the local ollama server at `http://127.0.0.1:1234`.

## Design

### Architecture
- Replace the embedding generation logic in `data_service.py` with `ollama-python`.
- Use the local ollama server for embeddings and RAG.
- Maintain compatibility with the chat interface in `chat_page.py`.

### Components
1. **Embedding Service** (`data_service.py`):
   - Replace SentenceTransformers logic with `ollama-python`.
   - Generate embeddings using the local ollama server.
2. **RAG Pipeline** (`data_service.py`):
   - Extend or replace existing RAG logic to work with `ollama-python`.
3. **Chat Interface** (`chat_page.py`):
   - Ensure compatibility with the new embedding and RAG pipeline.

### Data Flow
1. User uploads a document (PDF, TXT, DOCX, or image).
2. The document is processed and converted to text.
3. Text is split into chunks for embedding generation.
4. Embeddings are generated using `ollama-python` via the local server.
5. RAG retrieves relevant context based on user queries.
6. Responses are displayed in the chat interface.

### Error Handling
- **Ollama Server Unavailable**:
  - Implement a retry mechanism (3 retries with exponential backoff).
  - Fallback to cached embeddings or a default response if the server remains unavailable.
  - Log errors for debugging and monitoring.
- **Embedding Generation Failures**:
  - Handle invalid input or server errors during embedding generation.
  - Return user-friendly error messages (e.g., "Failed to generate embeddings. Please try again later.").
- **RAG Pipeline Errors**:
  - Gracefully handle failures during RAG retrieval (e.g., empty results, timeouts).
  - Provide fallback responses if the pipeline fails.

### Testing with pytest
- **Test Cases**:
  - Embedding generation with valid and invalid inputs.
  - Mock the ollama server to simulate success and failure scenarios.
  - RAG retrieval with mock embeddings and queries.
  - Verify handling of edge cases (e.g., no relevant context).
  - Test fallback responses when the ollama server is unavailable.
- **Test Structure**:
  - Use `pytest` fixtures to mock dependencies.
  - Organize tests in a dedicated directory (`tests/`).

### README Updates
- **Installation Instructions**:
  - Replace `pip install -r requirements.txt` with `uv pip install -r requirements.txt`.
  - Add a note to ensure `uv` is installed and configured.
  - Example:
    ```bash
    uv pip install -r requirements.txt
    ```
- **Running the Application**:
  - Update the run command to use `uv`:
    ```bash
    uv run python main.py
    ```
  - Add a note about ensuring the ollama server is running at `http://127.0.0.1:1234`.
- **Documentation**:
  - Add a section titled "RAG with ollama-python" to explain:
    - Integration of `ollama-python` for embeddings and RAG.
    - Requirements (e.g., running the ollama server).
    - How to switch between local and ollama embeddings (if applicable).

### Fixing Run Issues
- **Missing Dependencies**:
  - Ensure all dependencies, including `ollama-python`, are listed in `requirements.txt` or `pyproject.toml`.
  - Add a note in the README to install missing dependencies using `uv`.
- **Ollama Server Configuration**:
  - Verify that the ollama server is running before starting the application.
  - Add error messages if the server is unavailable.
- **Environment Setup**:
  - Document environment-specific requirements (e.g., Python version, `uv` setup).
  - Provide troubleshooting steps for common issues (e.g., port conflicts, missing dependencies).

## Success Criteria
1. The application successfully integrates `ollama-python` for embeddings and RAG.
2. All existing functionality remains compatible with the new integration.
3. Error handling is robust, providing fallback responses when the ollama server is unavailable.
4. Tests pass for embedding generation, RAG pipeline, and error scenarios.
5. The README is updated to reflect the changes and provide clear instructions for installation and usage.

## Open Questions
- Should there be a mechanism to switch between local (SentenceTransformers) and ollama embeddings dynamically?
- Are there specific ollama models or configurations that should be prioritized?

---