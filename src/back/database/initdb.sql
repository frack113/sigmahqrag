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

-- embedding_config
CREATE TABLE IF NOT EXISTS embedding_config (
    doc_type TEXT PRIMARY KEY,
    model TEXT NOT NULL DEFAULT '',
    chunk_size INTEGER DEFAULT 512,
    overlap INTEGER DEFAULT 50
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

-- doc_sigma_ref
CREATE TABLE IF NOT EXISTS doc_sigma_ref (
    url_hash TEXT PRIMARY KEY,
    original_url TEXT NOT NULL,
    normalized_url TEXT,
    content_type TEXT,
    rule_id TEXT,
    title TEXT,
    timestamp TEXT,
    content_sha256 TEXT,
    embed_status TEXT DEFAULT 'pending'
);

-- doc_registry (for file discovery results)
CREATE TABLE IF NOT EXISTS doc_registry (
    url_hash TEXT PRIMARY KEY,
    org TEXT,
    repo TEXT,
    content_type TEXT,
    file_name TEXT,
    content_sha256 TEXT,
    file_size BIGINT,
    original_url TEXT,
    normalized_url TEXT,
    rule_id TEXT DEFAULT '00000000-0000-0000-0000-000000000000',
    title TEXT,
    timestamp TEXT,
    last_seen TEXT,
    status TEXT,
    embed_status TEXT DEFAULT 'pending'
);

-- git_metadata
CREATE TABLE IF NOT EXISTS git_metadata (
    repo_key TEXT PRIMARY KEY,
    metadata TEXT NOT NULL
);

-- git_selected_dirs
CREATE TABLE IF NOT EXISTS git_selected_dirs (
    repo_key TEXT NOT NULL,
    dir_path TEXT NOT NULL,
    updated TEXT,
    PRIMARY KEY (repo_key, dir_path)
);

-- worker_state (worker lifecycle tracking)
CREATE TABLE IF NOT EXISTS worker_state (
    worker_type TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'idle',
    last_heartbeat TEXT,
    current_task_id TEXT DEFAULT '',
    started_at TEXT,
    error TEXT DEFAULT ''
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_models_type ON models(model_type);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON system_prompts(name);
CREATE INDEX IF NOT EXISTS idx_doc_sigma_ref_rule ON doc_sigma_ref(rule_id);
CREATE INDEX IF NOT EXISTS idx_doc_sigma_ref_timestamp ON doc_sigma_ref(timestamp);
CREATE INDEX IF NOT EXISTS idx_doc_sigma_ref_embed ON doc_sigma_ref(embed_status);
CREATE INDEX IF NOT EXISTS idx_doc_registry_embed ON doc_registry(embed_status);

-- =========================================================================
-- SEED DATA
-- =========================================================================

-- Embedding config defaults
INSERT OR IGNORE INTO embedding_config (doc_type, model, chunk_size, overlap) VALUES
    ('markdown', 'sentence-transformers/all-MiniLM-L6-v2', 512, 50);

-- Default system prompt for RAG chat
INSERT OR IGNORE INTO system_prompts (id, name, description, content, is_active) VALUES
    ('default-rag',
     'default-rag',
     'Default RAG assistant for SigmaHQ rules',
     'You are a security analyst assistant specializing in Sigma detection rules. '
     'Answer questions based on the provided context from the knowledge base. '
     'If the context does not contain enough information, say so clearly. '
     'Always cite the source rule or document when referencing specific detections.',
     TRUE);

-- Default app config
INSERT OR IGNORE INTO config (key, value) VALUES
    ('app_version', '"0.1.0"'),
    ('theme', '"dark"');
