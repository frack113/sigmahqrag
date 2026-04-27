# API Test Scripts

Scripts to test each API endpoint. Requires the API server to be running on `http://localhost:7860`.

## Usage

Run a script directly:

```bash
uv run scripts/test_health.py
```

Some scripts require admin authentication (password defaults to "admin").

## Scripts

| Script | Endpoint | Auth Required |
|--------|----------|---------------|
| `test_health.py` | GET /health | No |
| `test_auth_login.py` | POST /auth/login | No |
| `test_search_rules.py` | POST /api/search-rules | No |
| `test_documents_ingest.py` | POST /documents/ingest | Yes |
| `test_feedback.py` | POST /feedback, GET /feedback/stats | No / Yes |
| `test_llm_list_files.py` | GET /llm/list-files/{repo_id} | No |
| `test_llm_download.py` | POST /llm/download | No |
| `test_llm_installed.py` | GET /llm/installed | No |
| `test_llm_delete.py` | DELETE /llm/{repo_id} | Yes |
| `test_embeddings_search.py` | GET /embeddings/search | No |
| `test_embeddings_files.py` | GET /embeddings/{repo_id}/files | No |
| `test_embeddings_installed.py` | GET /embeddings/installed | No |
| `test_embeddings_embed.py` | POST /embeddings/embed | No |
| `test_embeddings_admin_download.py` | POST /embeddings/admin/download | Yes |
| `test_admin_health.py` | GET /admin/health | Yes |
| `test_admin_llama.py` [start/stop] | POST /admin/llama/start, /admin/llama/stop | Yes |
| `test_admin_qdrant.py` [start/stop] | POST /admin/qdrant/start, /admin/qdrant/stop | Yes |
| `test_admin_stats.py` | GET /admin/ | Yes |
| `test_coverage.py` | GET /check-coverage | No |