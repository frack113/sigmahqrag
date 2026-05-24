# sigmahqrag — Agent Guide

## Project
SigmaHQ RAG — Local RAG system for Sigma detection rules.
- **Backend**: FastAPI + Jinja2 templates
- **Database**: DuckDB (metadata, worker state, config)
- **Vector Store**: Qdrant (auto-managed subprocess)
- **LLM**: llama.cpp (`127.0.0.1:8080`)
- **RAG Pipeline**: LlamaIndex
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Python**: 3.12+, dependency manager: `uv`

## Entry point & dev server
- `python main.py` starts FastAPI on port 7860 with hot reload (uvicorn factory: `src.main:create_app`)
- Always use `uv run` for commands (uv.lock present, dependency manager is `uv`)

## Environment
- **OS**: Windows
- **Shell**: PowerShell 5.1

## Commands
| Action | Command |
|---|---|
| Serve | `uv run python main.py` |
| Test all | `uv run pytest` |
| Single test | `uv run pytest tests/path/to/test.py::test_name -v` |
| Lint | `uv run ruff check .` |
| Typecheck | `uv run mypy .` |

## Project layout
```
main.py              — dev server launcher
src/
  main.py            — FastAPI app factory + lifespan (config init, Qdrant auto-start)
  api/               — FastAPI routes
    v1/              — JSON API endpoints (admin, chat, config, coverage, dispatcher, duckdb,
                       documents, embedding_config, embeddings, explain, feedback, files,
                       github, llamacpp, logs, models, qdrant, search, system_prompt)
    routes/          — Page routes (page_admin, page_chat, page_data, page_duckdb)
  back/              — backend services
    backend/         — Core backend services (cache.py, chat_service.py)
    database/        — DuckDB service + models
    documents/       — Document parsing, validation, indexing, sigma_ref downloader
    embedding_config.py — Embedding type config (stored in DuckDB)
    feedback/        — Feedback service + repository + models
    github/          — GitHub API + git operations
    llamacpp/        — llama.cpp client, service, health check, VRAM estimation
    models/          — Model download, registry, types, exceptions
    qdrant/          — Qdrant client, service, collections, auto-start, downloader, health, storage
    rag/             — RAG pipeline, search, embeddings, chunker, ingestion, transforms, indices, queries
    system_prompt.py — System prompt management (stored in DuckDB)
    update_manager.py — Update/version management
    utils/           — File utilities, file type identification
    service_manager.py — Service lifecycle management
  worker/            — background workers
    base.py          — Base worker classes
    processor.py     — Task dispatcher
    enums.py         — Worker name enums
    workers/         — Individual workers
      github_discovery_worker.py
      github_embedding_worker.py
      local_discovery_worker.py
      local_embedding_worker.py
      sigmaref_discovery_worker.py
      sigmaref_embedding_worker.py
      model_sync_worker.py
      local_repo_sync_worker.py
      embedding_base.py
  front/             — Jinja2 templates + static assets
    templates/       — HTML templates
      admin/         — Admin pages (dashboard, models, llama, qdrant, health, logs, system_prompts, overview, backend)
      data/          — Data pages (overview, github, embedding, vectordb)
      duckdb/        — DuckDB explorer pages
      prompts/       — Jinja2 prompt templates (search_answer.j2, explain_rule.j2, coverage_analysis.j2)
      shared/        — Shared layout components (layout.html, _header.html)
      base.html      — Base template
      chat.html      — Chat page template
      admin.html     — Admin base template
    static/
      css/           — Stylesheets
        _shared-layout.css — Shared layout, cards, buttons, forms (source of truth for shared patterns)
        admin.css    — Admin page-specific styles
        chat.css     — Chat page (standalone dark theme)
        data.css     — Data page-specific styles
        duckdb.css   — DuckDB page styles
        github.css   — GitHub page styles
        main.css     — Main styles
        overview.css — Overview page styles
        vectordb.css — Vector DB page styles
      js/            — JavaScript (admin.js, chat.js, data.js, duckdb.js, qdrant.js, vectordb.js)
  shared/            — Shared utilities
    config.py        — Central configuration (dataclass + TOML + DuckDB overrides)
    download_manager.py
    exceptions.py    — SigmaError and custom exceptions
    health.py        — Health check utilities
    schemas/         — Pydantic schemas (chat, search, download, github_repo, qdrant, sigma_rule, update, chat_mode)
    subprocess_manager.py
    temp_manager.py
    toml_service.py
    utils.py
    version_manager.py
tests/
  unit/              — isolated unit tests
  integration/       — app-dependent tests (server must be running)
  admin/             — admin endpoint tests
  evals/             — RAG accuracy evaluation
  conftest.py        — pytest fixtures
data/                — runtime data
  sigmahqrag.toml    — Main config file (services, paths, logging)
  sigmahqrag.db      — SQLite fallback (if used)
  duckdb/            — DuckDB database storage
  bin/               — Downloaded binaries
    qdrant/          — Qdrant binary + config + static web UI
    llamacpp/        — llama.cpp binaries (llama-server.exe, llama-cli.exe, etc.)
  models/            — Downloaded GGUF models
    llm/             — LLM models
    embeddings/      — Embedding models
    registry.json    — Model registry
  logs/              — Application logs
  pids/              — Process ID files
  qdrant_storage/    — Qdrant vector storage
  temp/              — Temporary files
  documents/         — Downloaded/cached documents
    sigmaref/        — Sigma reference documents
  rag_cache/         — RAG pipeline cache
templates/
  config.yaml.j2     — Qdrant config template
```

## Architecture facts
- **Qdrant**: auto-managed subprocess. Binary downloaded from GitHub on first start if missing, stored in `data/bin/qdrant/`. Controlled via `data/sigmahqrag.toml` (`qdrant_manage_internally: bool`).
- **llama.cpp**: runs on `127.0.0.1:8080`. Binary downloaded from GitHub releases, stored in `data/bin/llamacpp/`. Full module in `src/back/llamacpp/` with client, service, health check, and VRAM estimation.
- **Config**: `data/sigmahqrag.toml` loaded via dataclass in `src/shared/config.py`. Additional configs (embedding types, system prompts) are stored in **DuckDB**, not in separate TOML files.
- **Embeddings**: HuggingFace `sentence-transformers/all-MiniLM-L6-v2`, 384-dim vectors.
- **RAG**: LlamaIndex-based pipeline in `src/back/rag/`.
- **Models**: GGUF files downloaded from HuggingFace, managed via `src/back/models/`.
- **Chat page** (`/chat`): simplified Mistral-like interface. No mode selector, no file upload. Always uses `mode: "search"`.
  - Page route: `src/api/routes/page_chat.py` → template `src/front/templates/chat.html`
  - Streaming API: `POST /api/v1/chat/message/stream` (SSE) → `src/api/v1/chat.py`
  - Backend service: `src/back/backend/services/chat_service.py` → dispatches to `RAGPipeline` + `SearchEngine`
  - Frontend: `src/front/static/js/chat.js` + `src/front/static/css/chat.css`
- **Prompt templates**: Jinja2 files in `src/front/templates/prompts/` (`search_answer.j2`, `explain_rule.j2`, `coverage_analysis.j2`). Only `search_answer.j2` is actively used by the chat UI.

## API v1 Endpoints
All endpoints under `/api/v1/`:
| Module | Endpoints |
|---|---|
| `admin.py` | Admin status, download controls, task cancellation |
| `chat.py` | Chat message (streaming SSE), chat history |
| `config.py` | Configuration management |
| `coverage.py` | Coverage analysis |
| `dispatcher.py` | Task dispatcher controls |
| `duckdb.py` | DuckDB explorer API |
| `documents.py` | Document management |
| `embedding_config.py` | Embedding type configuration |
| `embeddings.py` | Embedding operations |
| `explain.py` | Rule explanation |
| `feedback.py` | User feedback |
| `files.py` | File operations |
| `github.py` | GitHub repository management |
| `llamacpp.py` | llama.cpp service controls |
| `logs.py` | Log access |
| `models.py` | Model management |
| `qdrant.py` | Qdrant collection management |
| `search.py` | Vector search |
| `system_prompt.py` | System prompt management |

## Page Routes
| Route | Module | Template |
|---|---|---|
| `/admin/*` | `page_admin.py` | `src/front/templates/admin/*.html` |
| `/chat` | `page_chat.py` | `src/front/templates/chat.html` |
| `/data/*` | `page_data.py` | `src/front/templates/data/*.html` |
| `/duckdb/*` | `page_duckdb.py` | `src/front/templates/duckdb/*.html` |

## Workers
Background workers managed by `TaskDispatcher`:
| Worker | Purpose |
|---|---|
| `github_discovery_worker` | Discover documents in GitHub repos |
| `github_embedding_worker` | Embed documents from GitHub repos |
| `local_discovery_worker` | Discover documents in local repos |
| `local_embedding_worker` | Embed documents from local repos |
| `sigmaref_discovery_worker` | Discover Sigma reference documents |
| `sigmaref_embedding_worker` | Embed Sigma reference documents |
| `model_sync_worker` | Sync downloaded models with registry |
| `local_repo_sync_worker` | Sync local repositories |

## Testing quirks
- `asyncio_mode = auto` in pytest config, no need to mark async tests explicitly
- Fixtures: `sample_sigma_rule` (dict), `valid_sigma_rule_yml` (str), `sample_documents` in `tests/conftest.py`
- YAML fixtures in `tests/fixtures/` (`valid_sigma_rule.yml`, `invalid_missing_fields.yml`)
- Integration tests (`tests/integration/`) need the server running

## Linting & style
- Ruff: line-length 100, target py312. Rules selected: E, F, W, I, N, UP, B, A, C4, PT (with E501, B008 ignored)
- mypy: `strict = false` with many packages ignored (gradio, fastapi, qdrant_client, llama_index, etc.)
- Disallowed untyped defs follow per-file overrides in `mypy.ini`

## Frontend — shared CSS patterns
- **Card component**: Always use `<div class="card">` for content containers. Defined in `src/front/static/css/_shared-layout.css` with `.card`, `.card-header`, `.card-body`, `.cards-grid`. Do NOT redefine `.card` in section-specific CSS files.
- **Buttons**: Use shared classes `btn`, `btn-primary`, `btn-success`, `btn-danger`, `btn-secondary`. Defined in `src/front/static/css/_shared-layout.css` (lines 347-395). Do NOT redefine button styles per-page.
- **Layout**: `_shared-layout.css` is the source of truth for shared UI patterns. Section files (`admin.css`, `data.css`, `duckdb.css`, etc.) should only contain page-specific styles.
- **Chat page** (`chat.css`): standalone full-height dark layout. Does NOT use shared card/btn patterns. Has its own `.message`, `.chat-layout`, `.chat-input-bar`, `.chat-messages` classes. Must remain self-contained.

## Warnings
- Project is WIP — many things may be incomplete or half-refactored per README

## Git hooks — `.git/hooks/`
Uses **pre-commit** package (`.pre-commit-config.yaml`). Enforces:
1. **`.gitignore` compliance** — rejects ignored files (e.g. `data/`, `.opencode/`, `venv/`) via `scripts/check_ignored.py`
2. **`ruff check`** (auto-fix) on staged `.py` files
3. **`ruff format`** (black-compatible) on staged `.py` files

Install: `uv run pre-commit install`. Run all hooks: `uv run pre-commit run --all-files`.
Bypass with `git commit --no-verify` if needed.

Other hooks (`post-checkout`, `post-commit`, `post-merge`, `pre-push`) are Git LFS stubs — they call `git-lfs` hooks. Safe to ignore if not using LFS.

## GitHub CI/CD — `.github/workflows/`
| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | Push (toutes branches) + PR (main) | `lint-typecheck` — ruff + black checks sur ubuntu-latest avec uv |

Le workflow CI utilise:
- `astral-sh/setup-uv@v6` pour gérer les dépendances
- Python 3.12
- Vérifie: `uv run ruff check main.py src/ tests/` et `uv run black --check main.py src/ tests/`

## BMad Artifacts
- **Outputs**: `_bmad-output/` contains `planning-artifacts` and `implementation-artifacts`.

- **Skill Directory**: `.opencode/skills/{skill_name}/`
- **Skill Definition**: Each skill has a `SKILL.md` file at its root directory (`.opencode/skills/{skill_name}/SKILL.md`).
- **Workflow Steps**: Step files (e.g., `step-01-xxx.md`) are located within the skill's directory: `.opencode/skills/{skill_name}/step-01-xxx.md`.
- **Skill Artifacts**: Skills may contain additional context or templates (e.g., `checklist.md`, `spec-template.md`, `template.md`, `discover-inputs.md`) in the same `{skill_name}` directory.
- **Customization**: Each skill can have a `customize.toml` file for overrides.
