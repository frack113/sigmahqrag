# API Test Scripts

Scripts to test each API endpoint. Requires the API server to be running on `http://localhost:7860`.

## Usage

Run a script directly:

```bash
uv run scripts/test_health.py
```

Some scripts require admin authentication (password defaults to "admin").

## Unified Admin APIs

### LLM Admin (`/admin/llm`)

```bash
# List GGUF files for a model
uv run scripts/test_api_admin_llm.py list <repo_id>

# Get model info
uv run scripts/test_api_admin_llm.py info <repo_id>

# List installed models
uv run scripts/test_api_admin_llm.py installed

# Download a model
uv run scripts/test_api_admin_llm.py download [-f] <repo_id> [filename]

# Delete a model or specific file
uv run scripts/test_api_admin_llm.py delete [-f] <repo_id> [filename]
```

### Embeddings Admin (`/admin/embeddings`)

```bash
# List installed embedding models
uv run scripts/test_api_admin_embeddings.py installed

# Get model info
uv run scripts/test_api_admin_embeddings.py info <repo_id>

# Download an embedding model (full repo via snapshot_download)
uv run scripts/test_api_admin_embeddings.py download [-f] <repo_id>

# Delete an embedding model
uv run scripts/test_api_admin_embeddings.py delete [-f] <repo_id>
```

## Legacy Scripts

| Script | Endpoint | Notes |
|--------|----------|-------|
| `test_health.py` | GET /health | |
| `test_auth_login.py` | POST /auth/login | |
| `test_search_rules.py` | POST /api/search-rules | |
| `test_documents_ingest.py` | POST /documents/ingest | Auth required |
| `test_feedback.py` | POST /feedback, GET /feedback/stats | |
| `test_admin_health.py` | GET /admin/health | Auth required |
| `test_admin_llama.py` [start/stop] | POST /admin/llama/start, /admin/llama/stop | Auth required |
| `test_admin_qdrant.py` [start/stop] | POST /admin/qdrant/start, /admin/qdrant/stop | Auth required |
| `test_admin_stats.py` | GET /admin/ | Auth required |
| `test_coverage.py` | GET /check-coverage | |

## Options

- `-f, --force`: Skip confirmation prompt
- `-n, --filename`: Specify filename (for LLM downloads)
- `--url`: Override default base URL (default: http://localhost:7860)