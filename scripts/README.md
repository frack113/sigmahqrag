# API Test Scripts

Scripts to test each API endpoint. Requires the API server to be running on `http://localhost:7860`.

## Usage

Run a script directly:

```bash
uv run scripts/test_health.py
```

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

### Backend Admin (`/admin/backend`)

Manages binary downloads for llama.cpp and qdrant.

```bash
# Start a binary download (GET /admin/backend/?action=download)
uv run scripts/test_api_admin_backend.py download --service <llama|qdrant> [--version <ver>]

# Cancel a download (POST /admin/backend/?action=cancel)
uv run scripts/test_api_admin_backend.py cancel --download-id <id>

# Get download progress via SSE stream (GET /admin/backend/?action=progress)
uv run scripts/test_api_admin_backend.py progress --download-id <id>

# Get update status (GET /admin/backend/?action=status)
uv run scripts/test_api_admin_backend.py status
```

### Services Admin (`/admin/services`)

Start, stop and monitor llama.cpp and qdrant services.

```bash
# Start a service (POST /admin/services/?action=start)
uv run scripts/test_api_admin_service.py start --service <llama|qdrant> [--model-path <path>]

# Stop a service (POST /admin/services/?action=stop)
uv run scripts/test_api_admin_service.py stop --service <llama|qdrant>

# Get service logs (GET /admin/services/?action=logs)
uv run scripts/test_api_admin_service.py logs --service <llama|qdrant>
```

## Options

- `-f, --force`: Skip confirmation prompt
- `-n, --filename`: Specify filename (for LLM downloads)
- `--url`: Override default base URL (default: http://localhost:7860)
- `--service`: Service name (llama, qdrant) for backend and services scripts
- `--download-id`: Download ID for cancel/progress actions
- `--version`: Version to download (default: latest)
- `--model-path`: Model path for llama service start
