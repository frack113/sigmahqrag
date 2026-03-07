# Refactoring Plan: LangChain Integration and Architecture Improvement

## Overview
This document outlines the comprehensive refactoring plan to ensure consistent LangChain usage, improve code architecture, and remove outdated components in the SigmaHQ RAG project.

## Current State Analysis

### ✅ Working Components
1. **Chat Service** (`src/nicegui_app/models/chat_service.py`)
   - Properly uses `langchain_openai.ChatOpenAI`
   - Correct imports and initialization
   - Functional LLM integration with Ollama

2. **Dependencies** (`pyproject.toml`)
   - All required LangChain packages declared:
     - `langchain>=1.2.10`
     - `langchain-community>=0.4.1`
     - `langchain-openai>=1.1.10`
   - Imports verified and working

3. **Small, Focused Services**
   - `RepositoryService` - Clean, focused implementation
   - `FileProcessor` - Clean, focused implementation

### ❌ Issues Identified

1. **RAG Service** (`src/nicegui_app/models/rag_service.py`)
   - Uses direct Ollama client instead of LangChain's embedding models
   - Uses direct ChromaDB client instead of LangChain's vector store integration
   - Not aligned with project's LangChain usage pattern

2. **Large, Monolithic Files**
   - `chat_service.py` - Too large, mixes multiple responsibilities
   - `data_service.py` - Too large, acts as a facade but needs simplification

3. **Outdated Tests**
   - All pytest test files reference outdated code
   - Need to be removed before implementation

## Proposed Architecture Changes

### 1. Split `chat_service.py` into Smaller Files

#### New File Structure:
```
src/nicegui_app/models/
├── chat_service.py          # Core chat logic (simplified)
├── document_processor.py    # Document processing (new)
├── llm_service.py           # LLM integration (new)
├── rag_service.py           # Update to use LangChain
├── repository_service.py    # GitHub operations (already small)
├── file_processor.py        # File operations (already small)
└── data_service.py          # Simplify or remove
```

#### File Breakdown:

**`chat_service.py`** (Simplified)
- Message history management
- Conversation state management
- Message export/import functionality
- Remove document processing and LLM logic

**`document_processor.py`** (New)
- PDF processing and text extraction
- Image processing and OCR
- DOCX processing
- Text file processing
- Base64 preview generation

**`llm_service.py`** (New)
- ChatOpenAI integration
- Response generation
- Context building
- Error handling and fallbacks

### 2. Update `rag_service.py` to Use LangChain

#### File: `src/nicegui_app/models/rag_service.py`

**Changes Required:**

1. **Add LangChain Imports**
   ```python
   from langchain_community.embeddings import OllamaEmbeddings
   from langchain_community.vectorstores import Chroma
   ```

2. **Modify `_initialize_rag()` Method**
   - Replace direct Ollama client with `OllamaEmbeddings`
   - Replace direct ChromaDB client with `Chroma` vector store
   - Maintain backward compatibility with existing API

3. **Update Embedding Generation**
   - Use `OllamaEmbeddings.embed_documents()` instead of direct Ollama API calls
   - Simplify embedding generation logic

4. **Update Vector Store Operations**
   - Use `Chroma.from_texts()` for initialization
   - Use `Chroma.similarity_search()` for retrieval
   - Maintain existing metadata handling

### 3. Simplify `data_service.py`

**Options:**
- **Option A**: Keep as thin facade, remove delegated methods
- **Option B**: Remove entirely, use services directly
- **Option C**: Keep minimal coordination logic only

**Recommended**: Option A - Keep as thin coordinator, remove redundant delegation

### 4. Remove Outdated Test Files

**Files to Remove:**
- `tests/test_chat_service.py`
- `tests/test_data_service.py`
- `tests/test_github_repo_config.py`
- `tests/test_github_repo_display.py`
- `tests/test_github_repo_grid.py`
- `tests/test_github_repo_removal.py`

## Implementation Details

### Before (Current Implementation)

**RAG Service:**
```python
from ollama import Client

class RagService:
    def __init__(self, embedding_model_name: str = 'all-MiniLM-L6-v2'):
        self.ollama_client = Client(host='http://127.0.0.1:1234')
        self.chroma_client = chromadb.PersistentClient(path=".chromadb")
        self.collection = self.chroma_client.get_or_create_collection(...)
```

**Chat Service (Monolithic):**
```python
class ChatService:
    # Message history management
    # Document processing (PDF, images, DOCX, text)
    # LLM integration
    # Response generation
    # Export/import functionality
```

**DataService (Large Facade):**
```python
class DataService:
    # Orchestrates RagService, RepositoryService, FileProcessor
    # Many delegated methods
```

### After (Proposed Implementation)

**RAG Service:**
```python
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

class RagService:
    def __init__(self, embedding_model_name: str = 'all-MiniLM-L6-v2'):
        self.embeddings = OllamaEmbeddings(
            model=embedding_model_name,
            base_url="http://127.0.0.1:1234"
        )
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=".chromadb"
        )
```

**Chat Service (Split):**
- `chat_service.py` - Core chat logic only
- `document_processor.py` - Document processing
- `llm_service.py` - LLM integration

**DataService (Simplified):**
```python
class DataService:
    def __init__(self, embedding_model_name: str = 'all-MiniLM-L6-v2'):
        self.rag_service = RagService(embedding_model_name=embedding_model_name)
        self.repository_service = RepositoryService()
        self.file_processor = FileProcessor()
    
    # Minimal coordination logic only
```

## Benefits

1. **Single Responsibility Principle** - Each file has one clear purpose
2. **Consistency** - All LangChain components use the same pattern
3. **Maintainability** - Changes are isolated to specific areas
4. **Testability** - Smaller, focused files are easier to test
5. **Future-Proof** - Better integration with LangChain ecosystem
6. **Type Safety** - Better IDE support and type hints
7. **Documentation** - Clearer code structure for future developers

## Risks

1. **API Changes**: LangChain API may change, requiring updates
2. **Performance**: Potential performance impact from abstraction layers
3. **Learning Curve**: Team needs to be familiar with LangChain patterns
4. **Migration Effort**: Significant refactoring required

## Testing Strategy

1. **Import Testing**
   - Verify all LangChain imports work correctly
   - Check for version compatibility

2. **Functionality Testing**
   - Test embedding generation
   - Test vector store operations
   - Test context retrieval
   - Test context storage
   - Test document processing
   - Test LLM integration

3. **Integration Testing**
   - Test with ChatService
   - Test with DataService
   - Test with GitHub repository indexing

## Migration Steps

1. ✅ Review project structure and dependencies
2. ✅ Examine all source files for LangChain usage
3. ✅ Test LangChain imports
4. ✅ Identify inconsistencies
5. ✅ Create refactoring documentation
6. ⏳ Remove outdated pytest test files
7. ⏳ Refactor chat_service.py into smaller files
8. ⏳ Create document_processor.py
9. ⏳ Create llm_service.py
10. ⏳ Update rag_service.py to use LangChain
11. ⏳ Simplify data_service.py
12. ⏳ Verify all imports work correctly
13. ⏳ Test the updated implementation

## Success Criteria

- All LangChain components use consistent patterns
- No import errors or warnings
- All RAG functionality works correctly
- Code follows Single Responsibility Principle
- No breaking changes to existing API
- Code passes linting and type checking
- No large, monolithic files remain
- Outdated tests removed

## References

- [LangChain Documentation](https://python.langchain.com/docs/)
- [LangChain Community](https://python.langchain.com/docs/integrations/)
- [Ollama LangChain Integration](https://python.langchain.com/docs/integrations/llms/ollama)
- [Project Dependencies](pyproject.toml)
- [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)

## Notes

- This refactoring is focused on consistency, architecture, and best practices
- No changes to public APIs or user-facing functionality
- Backward compatibility maintained where possible
- All changes are non-breaking
- Follows the pattern established by RepositoryService and FileProcessor
- Prioritize code quality and maintainability