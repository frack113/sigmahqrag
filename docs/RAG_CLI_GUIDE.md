# RAG CLI Guide

A comprehensive guide for using the Simple RAG CLI with ChromaDB integration.

## Overview

The RAG CLI provides a command-line interface for testing and working with Retrieval-Augmented Generation (RAG) functionality using local ChromaDB for vector storage. It's built on top of the existing RAG service in the SigmaHQ RAG application.

## Installation

The CLI is included in the project and can be run using uv:

```bash
# Install dependencies (if not already installed)
uv add chromadb

# Run the CLI
uv run python src/cli/rag_cli.py [command] [options]
```

## Commands

### 1. Info - Check System Status

Check the status of ChromaDB, LLM service, and system configuration.

```bash
uv run python src/cli/rag_cli.py info
```

**Output includes:**
- ChromaDB availability and configuration
- Persist directory status
- LLM service availability
- Collection statistics
- Test response from LLM

### 2. Store - Store Documents

Store text documents in the vector database for retrieval.

```bash
# Basic usage
uv run python src/cli/rag_cli.py store --id my_document --file document.txt

# With metadata
uv run python src/cli/rag_cli.py store --id my_document --file document.txt --metadata '{"author": "John Doe", "category": "technical"}'
```

**Options:**
- `--id`: Unique identifier for the document (required)
- `--file`: Path to the text file to store (required)
- `--metadata`: JSON string of metadata for the document (optional)

**Features:**
- Automatic text chunking (500 characters default, 100 overlap)
- Embedding generation using LM Studio
- Metadata storage with each chunk
- Progress reporting

### 3. Query - Retrieve and Generate

Query the vector database and get RAG-enhanced responses.

```bash
# Basic query
uv run python src/cli/rag_cli.py query "What is this document about?"

# With custom parameters
uv run python src/cli/rag_cli.py query "What technologies are mentioned?" --n-results 5 --min-score 0.2
```

**Options:**
- `--n-results`: Number of results to retrieve (default: 3)
- `--min-score`: Minimum similarity score threshold (default: 0.1)

**Output includes:**
- RAG-generated response using retrieved context
- Retrieved document chunks with similarity scores
- Document IDs and content previews

### 4. List - View Stored Documents

List all stored documents and their metadata.

```bash
uv run python src/cli/rag_cli.py list
```

**Shows:**
- Document IDs
- Number of chunks per document
- Source information
- Last similarity scores

### 5. Clear - Clear Database

Remove all documents from the vector database.

```bash
uv run python src/cli/rag_cli.py clear
```

### 6. Stats - System Statistics

Get detailed statistics about the RAG system.

```bash
uv run python src/cli/rag_cli.py stats
```

**Includes:**
- ChromaDB collection information
- Document counts
- Embedding model details
- Cache statistics
- LLM service status

### 7. GitHub - Repository Management

Update and manage GitHub repositories based on configuration.

```bash
# Update all enabled repositories
uv run python src/cli/rag_cli.py github

# Uses default config file at data/config.json
```

**Features:**
- Clones new repositories specified in configuration
- Updates existing repositories (git pull)
- Shows repository information (branch, latest commit, file count)
- Supports concurrent repository operations
- Integrates with existing repository service

**Configuration:**
The command uses the configuration file at `data/config.json` which should contain:
```json
{
  "repositories": [
    {
      "url": "https://github.com/user/repo",
      "branch": "main",
      "enabled": true,
      "file_extensions": [".md", ".py"]
    }
  ]
}
```

**Output includes:**
- Repository update status
- Latest commit information
- Branch information
- File counts
- Any errors encountered during updates

### 8. Update-DB - Database Update

Update the vector database by indexing files from GitHub repositories.

```bash
# Update database using default config
uv run python src/cli/rag_cli.py update-db

# Uses default config file at data/config.json
```

**Features:**
- Updates GitHub repositories first (git clone/pull)
- Processes files based on configured file extensions
- Generates embeddings for all processed files
- Stores document chunks in the vector database
- Provides detailed progress reporting
- Uses existing repository and RAG services

**Workflow:**
1. Load repository configuration from `data/config.json`
2. Update all enabled GitHub repositories
3. Process files matching configured extensions (e.g., .md, .py)
4. Generate embeddings using LM Studio
5. Store processed content in ChromaDB vector database
6. Provide detailed statistics on processed files

**Configuration:**
Uses the same configuration as the GitHub command:
```json
{
  "repositories": [
    {
      "url": "https://github.com/SigmaHQ/sigma",
      "branch": "main",
      "enabled": true,
      "file_extensions": [".md", ".py", ".yaml", ".yml"]
    }
  ]
}
```

**Output includes:**
- Repository update status
- File processing progress
- Embedding generation status
- Database storage confirmation
- Final statistics (total documents, chunk counts)
- Performance metrics

## Configuration

### Command Line Options

```bash
# Specify custom persist directory
uv run python src/cli/rag_cli.py info --persist-dir ./my_chromadb

# Specify custom LM Studio URL
uv run python src/cli/rag_cli.py info --base-url http://localhost:5000
```

**Global Options:**
- `--persist-dir`: Directory to store ChromaDB data (default: .chromadb)
- `--base-url`: LM Studio server URL (default: http://localhost:1234)

## ChromaDB Information

### What is ChromaDB?

ChromaDB is a vector database optimized for AI applications. It stores embeddings (vector representations) of text and enables fast similarity search.

### Key Features

- **Vector Storage**: Stores high-dimensional embeddings of text chunks
- **Similarity Search**: Fast retrieval based on semantic similarity
- **Persistence**: Data persists between sessions in the specified directory
- **Metadata Support**: Each document chunk can have associated metadata
- **Collection Management**: Organizes documents into named collections

### Directory Structure

When using the default persist directory (`.chromadb`), ChromaDB creates:

```
.chromadb/
├── chroma.sqlite3          # SQLite database file
├── chroma.sqlite3-shm      # SQLite shared memory
├── chroma.sqlite3-wal      # SQLite write-ahead log
└── [collection-specific files]
```

### Performance Considerations

- **Chunk Size**: Default 500 characters provides good balance of context and retrieval precision
- **Overlap**: Default 100 characters overlap helps maintain context across chunk boundaries
- **Similarity Threshold**: Lower values (0.1) retrieve more results, higher values (0.5+) retrieve only very similar content
- **Result Count**: More results provide more context but may slow down generation

## LLM Integration

### Supported Models

The CLI works with any LM Studio-compatible model. The system is configured to use:

- **Default Model**: `mistralai/ministral-3-14b-reasoning`
- **API Endpoint**: `http://localhost:1234/v1/chat/completions`
- **Embedding Model**: `text-embedding-all-minilm-l6-v2-embedding`

### Model Requirements

For optimal RAG performance, your LLM should:
- Support the OpenAI-compatible API format
- Handle system prompts for context management
- Provide good reasoning capabilities for RAG tasks
- Support reasonable context window sizes

### Embedding Models

The system uses text embedding models to convert text into vectors:
- **Default**: `text-embedding-all-minilm-l6-v2-embedding`
- **Alternative**: Any compatible embedding model available in LM Studio
- **Quality**: Better embedding models improve retrieval accuracy

## Usage Examples

### Basic Workflow

1. **Check System Status**
   ```bash
   uv run python src/cli/rag_cli.py info
   ```

2. **Store a Document**
   ```bash
   uv run python src/cli/rag_cli.py store --id tech_doc --file technical_documentation.txt
   ```

3. **Query the Document**
   ```bash
   uv run python src/cli/rag_cli.py query "What are the key features mentioned?"
   ```

4. **View Statistics**
   ```bash
   uv run python src/cli/rag_cli.py stats
   ```

### Advanced Usage

**Storing Multiple Documents with Metadata:**
```bash
# Store user manual
uv run python src/cli/rag_cli.py store --id user_manual --file manual.txt --metadata '{"type": "manual", "version": "1.0"}'

# Store API documentation
uv run python src/cli/rag_cli.py store --id api_docs --file api_reference.md --metadata '{"type": "api", "language": "python"}'
```

**Custom Query Parameters:**
```bash
# Strict similarity matching
uv run python src/cli/rag_cli.py query "How do I configure the system?" --min-score 0.3 --n-results 2

# Broad search
uv run python src/cli/rag_cli.py query "What technologies are used?" --min-score 0.05 --n-results 10
```

**Working with Different Collections:**
```bash
# Create separate collections for different document types
uv run python src/cli/rag_cli.py info --persist-dir ./user_docs
uv run python src/cli/rag_cli.py info --persist-dir ./technical_docs
```

## Troubleshooting

### Common Issues

**1. ChromaDB Not Available**
```
Error: chromadb not available: No module named 'chromadb'
```
**Solution:** Install ChromaDB
```bash
uv add chromadb
```

**2. LM Studio Connection Error**
```
Error: Failed to connect to LM Studio at http://localhost:1234
```
**Solution:** 
- Ensure LM Studio is running
- Check the correct port number
- Verify the model is loaded

**3. Unicode Encoding Issues (Windows)**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```
**Solution:** The CLI automatically handles this, but you can also set:
```bash
set PYTHONIOENCODING=utf-8
```

**4. Empty Query Results**
```
No relevant documents found in the vector database.
```
**Solution:**
- Lower the `--min-score` threshold
- Check if documents were stored successfully
- Verify the query text matches document content

### Performance Optimization

**For Large Documents:**
- Use smaller chunk sizes (300-400 characters)
- Increase overlap (150-200 characters)
- Consider preprocessing to remove boilerplate text

**For Better Retrieval:**
- Use appropriate similarity thresholds (0.1-0.3)
- Store relevant metadata for filtering
- Consider document preprocessing (cleaning, summarization)

**For Faster Queries:**
- Use higher similarity thresholds to reduce context
- Limit the number of results (`--n-results`)
- Enable caching (built into the RAG service)

## Integration with Existing System

The CLI uses the same RAG service as the web application, ensuring consistency:

- **Shared Configuration**: Uses the same LLM settings and models
- **Shared Storage**: Documents stored via CLI are available in the web interface
- **Shared Embeddings**: Same embedding models and parameters
- **Shared Caching**: Cache is shared between CLI and web interface

## Development and Customization

### Modifying the CLI

The CLI source is located at `src/cli/rag_cli.py`. You can:

- Add new commands
- Modify default parameters
- Add new output formats
- Integrate with other tools

### Extending Functionality

**Adding New Commands:**
1. Add command to the argument parser
2. Implement the command logic in the `main()` function
3. Add help text and examples

**Customizing RAG Behavior:**
1. Modify the `RAGCLI` class initialization
2. Adjust chunking parameters
3. Change similarity thresholds
4. Add preprocessing steps

## Best Practices

1. **Document Organization**: Use meaningful document IDs and metadata
2. **Chunking Strategy**: Balance chunk size with context requirements
3. **Similarity Thresholds**: Start with default values and adjust based on results
4. **Regular Maintenance**: Periodically clear unused documents to maintain performance
5. **Backup**: Consider backing up the ChromaDB directory for important collections

## Support

For issues or questions:
- Check the project README for system requirements
- Verify LM Studio is properly configured
- Ensure all dependencies are installed
- Review the troubleshooting section above