# API Test Scripts#

This directory contains test scripts for the SigmaHQ RAG admin API endpoints.

## Prerequisites

- The application must be running (`python main.py` or `uv run python main.py`)
- Server listens on `http://localhost:7860`

## Available Scripts

### test_api_admin_github.py

Test script for the `/admin/github` endpoint.

**Actions supported:**

#### List all repositories
```bash
uv run python scripts/test_api_admin_github.py list
```

#### Get repository info
```bash
# Usage: info <org> <name>
uv run python scripts/test_api_admin_github.py info sigmahq sigma-specification
```

#### Clone repository
```bash
uv run python scripts/test_api_admin_github.py clone --org sigmahq --name sigma-specification --branch main
```

#### Update repository (git pull)
```bash
uv run python scripts/test_api_admin_github.py update sigmahq sigma-specification
```

#### Update metadata (extensions, branch)
```bash
uv run python scripts/test_api_admin_github.py update-metadata sigmahq sigma-specification --branch main --extensions "*.yml,*.yaml,*.md"
```

#### Delete repository
```bash
uv run python scripts/test_api_admin_github.py delete sigmahq sigma-specification
# Or force delete without confirmation
uv run python scripts/test_api_admin_github.py delete sigmahq sigma-specification -f
```

---

### test_api_admin_backend.py

Test script for the `/api/v1/{llama,qdrant}` endpoints (download, status, progress, cancel).

```bash
uv run python scripts/test_api_admin_backend.py --help
```

---

### test_api_admin_service.py

Test script for the `/admin/services` endpoint.

```bash
uv run python scripts/test_api_admin_service.py --help
```

---

### test_api_admin_llm.py

Test script for the `/admin/llm` endpoint.

```bash
uv run python scripts/test_api_admin_llm.py --help
```

---

### test_api_admin_embeddings.py

Test script for the `/admin/embeddings` endpoint.

```bash
uv run python scripts/test_api_admin_embeddings.py --help
```

---

## Repository Structure

Repositories are stored in `./data/github/{organization}/{name}/` with a `metadata.json` file containing:
- `org`: organization name
- `name`: repository name
- `branch`: default branch
- `extensions_to_index`: list of file extensions to index in Qdrant

## Complete Example

```bash
# Start the server (terminal 1)
cd D:\rootme\sigmahqrag
uv run python main.py

# Use the script (terminal 2)
cd D:\rootme\sigmahqrag

# Clone a repository
uv run python scripts/test_api_admin_github.py clone --org sigmahq --name sigma-specification --branch main

# View repository info
uv run python scripts/test_api_admin_github.py info sigmahq sigma-specification

# Set extensions to index
uv run python scripts/test_api_admin_github.py update-metadata sigmahq sigma-specification --extensions "*.yml,*.yaml"

# List all repositories
uv run python scripts/test_api_admin_github.py list
```
