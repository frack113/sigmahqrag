# SigmaHQ RAG

A local RAG system for Sigma detection rules.

## WIP

This project is under active development. Some features may be incomplete.

## Architecture

- **Backend**: FastAPI + Jinja2 templates
- **Database**: DuckDB (metadata, worker state, config)
- **Vector Store**: Qdrant (auto-managed subprocess)
- **LLM**: llama.cpp (runs on `127.0.0.1:8080`)
- **RAG Pipeline**: LlamaIndex
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)

## Quick Start

```bash
uv run main.py
```

Server starts on `http://localhost:7860` .


## Configuration

- `data/sigmahqrag.toml` — Main config (Qdrant mode, paths, versions)

## Testing

```bash
uv run pytest              # Run all tests
uv run pytest tests/path -v # Single test
uv run ruff check .        # Lint
uv run mypy .              # Typecheck
```



## Icon

Use Icône de Pense créatif l&#039;inspiration ampoule by Sumit Saengthong on <a href="https://icon-icons.com/fr/authors/940-sumit-saengthong">Icon-Icons.com</a>