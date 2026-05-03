# SigmaHQ RAG API Documentation

## Overview

Base URL: `http://localhost:7860`

## Table of Contents

1. [Admin Services](#admin-services)
2. [Chat](#chat)
3. [Search](#search)
4. [Admin v1](#admin-v1)
5. [Admin Pages](#admin-pages)
6. [Other Endpoints](#other-endpoints)

---

## Admin Services

**Prefix:** `/admin` | **Source:** `src/api/routes/admin_service.py`

### Health Check

```
GET /admin/health
```

Returns health status of all services.

**Response:**
```json
{
  "services": [
    {"name": "llama.cpp", "status": "running", "color": "green", "port": 8080, "url": "http://localhost:8080"},
    {"name": "qdrant", "status": "stopped", "color": "red", "port": 6333, "url": "http://localhost:6333"}
  ]
}
```

### Service Operations

```
GET /admin/services/?action=logs&service=llama|qdrant
POST /admin/services/?action=start|stop&service=llama|qdrant
```

**Query Parameters:**
- `action`: Action to perform (`logs`, `start`, `stop`)
- `service`: Service name (`llama`, `qdrant`)

**Example - Start llama.cpp:**
```bash
POST /admin/services/?action=start&service=llama
```

**Example - Stop llama.cpp:**
```bash
POST /admin/services/?action=stop&service=llama
```

**Example - Get logs:**
```bash
GET /admin/services/?action=logs&service=llama
```

---

### llama.cpp Management

#### Get Config

```
GET /admin/llama/config
```

Returns current OS and GPU configuration.

**Response:**
```json
{
  "gpu": "cuda",
  "os": "windows"
}
```

#### Set Config

```
POST /admin/llama/config
```

**Body:**
```json
{
  "os": "windows",
  "gpu": "cuda"
}
```

**GPU Options:** `cpu`, `cuda`, `hip`, `vulkan`

#### Get Info

```
GET /admin/llama/info
```

Returns current version and update availability.

**Response:**
```json
{
  "current_version": "b3084",
  "update_available": true,
  "latest_version": "b3090"
}
```

#### Download

```
POST /admin/llama/download
```

Starts download of llama.cpp binary.

**Response:**
```json
{
  "success": true,
  "download_id": "dl-abc123",
  "message": "Download started"
}
```

#### Update

```
POST /admin/llama/update
```

Updates to latest version.

**Response:**
```json
{
  "success": true,
  "download_id": "dl-abc123",
  "version": "b3090",
  "message": "Downloading llama.cpp vb3090"
}
```

---

## Chat

**Prefix:** (none) | **Source:** `src/api/routes/chat.py`

### Chat Page

```
GET /chat
```

Returns HTML chat interface.

### Send Message

```
POST /api/v1/chat/message
```

**Body:**
```json
{
  "message": "search for network connection rules",
  "mode": "search"
}
```

**Mode Options:** `search`, `coverage`, `explain`

**Response:**
```json
{
  "response": "Found 5 matching rules...",
  "results": [...]
}
```

### Stream Message

```
POST /api/v1/chat/message/stream
```

Same as `/api/v1/chat/message` but streams response.

### Upload Sigma Rule

```
POST /api/v1/chat/upload
```

**Body:** `multipart/form-data` with YAML file

**Response:**
```json
{
  "filename": "rule.yml",
  "valid": true,
  "rule_id": "winevent-sysmon-connection"
}
```

---

## Search

**Prefix:** (none) | **Source:** `src/api/routes/search.py`

### Search Rules

```
POST /api/search-rules
GET /search-rules
```

**Body/Query:**
```json
{
  "query": "powershell suspicious",
  "mode": "search"
}
```

**Mode Options:** `search`, `coverage`, `explain`

### Search Suggestions

```
GET /api/search-suggestions?q=powershell
```

**Query Parameters:**
- `q`: Search query

---

## Admin v1

**Prefix:** `/api/v1/admin` | **Source:** `src/api/v1/admin.py`

### Get Status

```
GET /api/v1/admin/status
```

Returns component health status.

**Response:**
```json
{
  "data": {
    "llama_cpp": {"status": "inactive"},
    "qdrant": {"status": "inactive"}
  },
  "status": "success"
}
```

### Get Hardware

```
GET /api/v1/admin/hardware
```

Returns hardware info.

**Response:**
```json
{
  "status": "success",
  "data": {
    "hardware": {...},
    "model_compatibility": {...}
  }
}
```

### Get Models

```
GET /api/v1/admin/models
```

Returns installed models list.

**Response:**
```json
{
  "status": "success",
  "data": {
    "models": [
      {"repo_id": "meta-llama/llama-3-8b", "filename": "gguf", "size_mb": 4800, "status": "ready"}
    ]
  }
}
```

### Delete Model

```
POST /api/v1/admin/models/delete
```

**Body:**
```json
{
  "repo_id": "meta-llama/llama-3-8b",
  "filename": "gguf"
}
```

### Get Config

```
GET /api/v1/admin/config
```

Returns full application config.

### Download (with Idempotency)

```
POST /api/v1/admin/download
```

**Headers:**
- `X-Idempotency-Key: (optional)` - For deduplication

### Cancel Job

```
POST /api/v1/admin/cancel
```

**Body:**
```json
{
  "job_id": "job-abc123"
}
```

---

## Admin Pages

**Prefix:** (none) | **Source:** `src/api/routes/admin_pages.py`

| Path | Description |
|------|-------------|
| GET /admin | Admin dashboard |
| GET /admin/models | Models management |
| GET /admin/settings | Settings page |
| GET /admin/health | Health check page |
| GET /admin/logs | Logs page |
| GET /admin/hardware | Hardware page |
| GET /admin/llama | llama.cpp management |

---

## Other Endpoints

| Path | Method | Source | Description |
|------|--------|--------|-----------|
| GET /health | - | Health check |
| GET / | - | Root (redirects to /admin) |
| GET /explain-rule | explain.py | Explain Sigma rule |
| POST /feedback | feedback.py | Submit feedback |
| GET /feedback | feedback.py | Get feedback |
| GET /feedback/stats | feedback.py | Feedback stats |
| GET /check-coverage | coverage.py | Coverage check (not implemented) |
| POST /documents/ingest | documents.py | Ingest Sigma rules |
| GET /embeddings/search | embeddings.py | Search embeddings |
| POST /api/v1/admin/bulk-delete-models | admin_bulk.py | Bulk delete models |
| GET /admin/prompts/ | admin_prompts.py | List prompts |
| POST /admin/prompts/ | admin_prompts.py | Create/update prompt |
| GET /admin/prompts/active | admin_prompts.py | Get active prompt |
| GET /admin/backend/ | admin_backend.py | Backend status/progress |
| POST /admin/backend/ | admin_backend.py | Download/cancel |

---

## Admin Backend (download/cancel)

**Prefix:** `/admin` | **Source:** `src/api/routes/admin_backend.py`

### Get Progress

```
GET /admin/backend/?action=progress&download_id=xxx
```

Returns Server-Sent Events (SSE) stream.

### Get Status

```
GET /admin/backend/?action=status
```

### Download Service

```
POST /admin/backend/?action=download&service=llama|qdrant&version=latest
```

**Response:**
```json
{
  "download_id": "dl-abc123",
  "status": "started",
  "service": "llama.cpp",
  "version": "latest"
}
```

### Cancel Download

```
POST /admin/backend/?action=cancel&download_id=dl-xxx
```

---

## Model Management

**Prefix:** `/admin/llm` | **Source:** `src/api/routes/admin_llm.py`

### List Models

```
GET /admin/llm/?action=installed
```

### Search Models

```
GET /admin/llm/?action=list&repo_id=meta-llama/llama-3-8b
```

### Download Model

```
POST /admin/llm/?action=download&repo_id=meta-llama/llama-3-8b&filename=gguf
```

### Delete Model

```
POST /admin/llm/?action=delete&repo_id=meta-llama/llama-3-8b&filename=gguf
```

---

## Embeddings

**Prefix:** `/embeddings` | **Source:** `src/api/routes/embeddings.py`

| Method | Path | Description |
|--------|------|------------|
| GET | /embeddings/search | Search models |
| GET | /embeddings/{repo_id}/files | List files |
| GET | /embeddings/installed | List installed |
| POST | /embeddings/embed | Generate embedding |

---

## Prompts

**Prefix:** `/admin/prompts` | **Source:** `src/api/routes/admin_prompts.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | /admin/prompts/ | List prompts |
| POST | /admin/prompts/ | Create/Update |
| GET | /admin/prompts/active | Get active |