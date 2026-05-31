-- SigmaHQ RAG - DuckDB Schema + Seed Data
-- Single source of truth for database initialization.
-- All CREATE TABLE are IF NOT EXISTS and INSERT are OR IGNORE for idempotency.

-- =========================================================================
-- SCHEMA
-- =========================================================================

-- config
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- embedding_config (single global config — one embedding model for all file types)
CREATE TABLE IF NOT EXISTS embedding_config (
    key TEXT PRIMARY KEY DEFAULT 'global',
    model TEXT NOT NULL DEFAULT 'intfloat/multilingual-e5-small'
);

-- system_prompts
CREATE TABLE IF NOT EXISTS system_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE
);

-- models
CREATE TABLE IF NOT EXISTS models (
    repo_id TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,
    local_path TEXT,
    file_size BIGINT DEFAULT 0,
    status TEXT DEFAULT 'ready',
    dimension INTEGER,
    index_path TEXT,
    files TEXT,
    updated_at TEXT
);

-- doc_registry (unified document registry for all sources: GitHub, local, sigmaref)
CREATE TABLE IF NOT EXISTS doc_registry (
    url_hash TEXT PRIMARY KEY,
    org TEXT,
    repo TEXT,
    content_type TEXT,
    file_name TEXT,
    content_sha256 TEXT,
    file_size BIGINT,
    original_url TEXT NOT NULL,
    normalized_url TEXT,
    rule_id TEXT DEFAULT '00000000-0000-0000-0000-000000000000',
    title TEXT,
    timestamp TEXT,
    last_seen TEXT,
    embed_status TEXT DEFAULT 'discovery'
);

-- git_metadata
CREATE TABLE IF NOT EXISTS git_metadata (
    repo_key TEXT PRIMARY KEY,
    org TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    branch TEXT NOT NULL
);

-- git_selected_dirs
CREATE TABLE IF NOT EXISTS git_selected_dirs (
    repo_key TEXT NOT NULL,
    dir_path TEXT NOT NULL,
    updated TEXT,
    PRIMARY KEY (repo_key, dir_path)
);

-- doc_error (failed URLs — 30x/40x errors to skip on retry)
CREATE TABLE IF NOT EXISTS doc_error (
    url_hash TEXT PRIMARY KEY,
    original_url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    error_code INTEGER,
    error_message TEXT,
    org TEXT,
    repo TEXT,
    timestamp TEXT
);

-- worker_state
CREATE TABLE IF NOT EXISTS worker_state (
    worker_type TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'idle',
    current_task_id TEXT,
    progress_percent DOUBLE DEFAULT 0.0,
    current_file TEXT,
    last_heartbeat TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_models_type ON models(model_type);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON system_prompts(name);
CREATE INDEX IF NOT EXISTS idx_doc_registry_embed ON doc_registry(embed_status);
CREATE INDEX IF NOT EXISTS idx_doc_registry_org_repo ON doc_registry(org, repo);

-- =========================================================================
-- SEED DATA
-- =========================================================================

-- Embedding config defaults (single global model)
INSERT OR IGNORE INTO embedding_config (key, model) VALUES
    ('global', 'intfloat/multilingual-e5-small');

-- Default app config
INSERT OR IGNORE INTO config (key, value) VALUES
    ('app_version', '"0.1.0"'),
    ('theme', '"dark"');
