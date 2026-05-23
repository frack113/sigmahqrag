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
| API test scripts | `uv run python scripts/test_api_admin_*.py` (need server running) |

## Project layout
```
main.py              — dev server launcher
src/
  main.py            — FastAPI app factory + lifespan (config init, Qdrant auto-start)
  api/               — FastAPI routes (v1/ = JSON API, routes/ = page routes)
  back/              — backend services (qdrant, models, documents, rag, github, feedback, database, etc.)
  worker/            — background workers (discovery, embedding, sync, etc.)
  front/             — Jinja2 templates + static assets
  shared/            — config, download manager, TOML service, subprocess manager, utils, schemas
tests/
  unit/              — isolated unit tests
  integration/       — app-dependent tests (server must be running)
  admin/             — admin endpoint tests
  evals/             — RAG accuracy evaluation
scripts/             — API test scripts (require running server)
data/                — runtime: config tomls, binaries, models, Qdrant storage, logs
templates/           — Qdrant config.yaml.j2 template
```

## Architecture facts
- **Qdrant**: auto-managed subprocess. Binary downloaded from GitHub on first start if missing, stored in `data/bin/qdrant/`. Controlled via `data/sigmahqrag.toml` (`qdrant_mode: managed|external`).
- **llama.cpp**: runs on `127.0.0.1:8080`. Binary downloaded from GitHub releases, stored in `data/bin/llamacpp/`.
- **Config**: `data/sigmahqrag.toml` loaded via dataclass in `src/shared/config.py`. Also `data/embedding.toml` (model/chunk) and `data/system_prompt.toml` (chat prompts).
- **Embeddings**: HuggingFace `sentence-transformers/all-MiniLM-L6-v2`, 384-dim vectors.
- **RAG**: LlamaIndex-based pipeline in `src/back/rag/`.
- **Models**: GGUF files downloaded from HuggingFace, managed via `src/back/models/`.

## Testing quirks
- `asyncio_mode = auto` in pytest config, no need to mark async tests explicitly
- Fixtures: `sample_sigma_rule` (dict), `valid_sigma_rule_yml` (str), `sample_documents` in `tests/conftest.py`
- YAML fixtures in `tests/fixtures/` (`valid_sigma_rule.yml`, `invalid_missing_fields.yml`)
- Integration tests (`tests/integration/`) need the server running
- Scripts in `scripts/` need the server running

## Linting & style
- Ruff: line-length 100, target py312. Rules selected: E, F, W, I, N, UP, B, A, C4, PT (with E501, B008 ignored)
- mypy: strict mode enabled but many packages ignored (gradio, fastapi, qdrant_client, llama_index, etc.)
- Disallowed untyped defs follow per-file overrides in `mypy.ini`

## Frontend — shared CSS patterns
- **Card component**: Always use `<div class="card">` for content containers. Defined in `src/front/static/css/_shared-layout.css` with `.card`, `.card-header`, `.card-body`, `.cards-grid`. Do NOT redefine `.card` in section-specific CSS files (`admin.css`, `data.css`).
- **Buttons**: Use shared classes `btn`, `btn-primary`, `btn-success`, `btn-danger`, `btn-secondary`. Defined in `src/front/static/css/data.css`. Do NOT redefine button styles per-page.
- **Layout**: `_shared-layout.css` is the source of truth for shared UI patterns. Section files (`admin.css`, `data.css`) should only contain page-specific styles.

## Warnings
- Project is WIP — many things may be incomplete or half-refactored per README

## Git hooks — `.git/hooks/`
A `pre-commit` hook (`hooks/pre-commit`) enforces:
1. **`.gitignore` compliance** — rejects ignored files (e.g. `data/`, `.opencode/`, `venv/`)
2. **`ruff check`** on staged `.py` files
3. **`black --check`** on staged `.py` files

Install: `cp hooks/pre-commit .git/hooks/pre-commit`. Bypass with `git commit --no-verify` if needed.

Other hooks (`post-checkout`, `post-commit`, `post-merge`, `pre-push`) are Git LFS stubs — they call `git-lfs` hooks. Safe to ignore if not using LFS.

## BMad Artifacts
- **Outputs**: `_bmad-output/` contains `planning-artifacts` and `implementation-artifacts`.

- **Skill Directory**: `.opencode/skills/{skill_name}/`
- **Skill Definition**: Each skill has a `SKILL.md` file at its root directory (`.opencode/skills/{skill_name}/SKILL.md`).
- **Workflow Steps**: Step files (e.g., `step-01-xxx.md`) are located within the skill's directory: `.opencode/skills/{skill_name}/step-01-xxx.md`.
- **Skill Artifacts**: Skills may contain additional context or templates (e.g., `checklist.md`, `spec-template.md`, `template.md`, `discover-inputs.md`) in the same `{skill_name}` directory.
- **Customization**: Each skill can have a `customize.toml` file for overrides.

