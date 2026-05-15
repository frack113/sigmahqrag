DDL: list[str] = [
    """CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS embedding_config (
        doc_type TEXT PRIMARY KEY,
        model TEXT NOT NULL DEFAULT '',
        chunk_size INTEGER DEFAULT 1024,
        overlap INTEGER DEFAULT 64
    )""",
    """CREATE TABLE IF NOT EXISTS system_prompts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        content TEXT NOT NULL,
        is_active BOOLEAN DEFAULT FALSE
    )""",
    """CREATE TABLE IF NOT EXISTS models (
        repo_id TEXT PRIMARY KEY,
        model_type TEXT NOT NULL CHECK(model_type IN ('llm', 'embeddings')),
        local_path TEXT,
        file_size BIGINT DEFAULT 0,
        status TEXT DEFAULT 'ready',
        dimension INTEGER,
        index_path TEXT,
        files TEXT,
        updated_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS doc_registry (
        url_hash TEXT PRIMARY KEY,
        original_url TEXT NOT NULL,
        normalized_url TEXT,
        content_type TEXT,
        rule_id TEXT,
        title TEXT,
        timestamp TEXT,
        content_sha256 TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS git_metadata (
        repo_key TEXT PRIMARY KEY,
        metadata TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS git_selected_dirs (
        repo_key TEXT NOT NULL,
        dir_path TEXT NOT NULL,
        updated TEXT,
        PRIMARY KEY (repo_key, dir_path)
    )""",
    """CREATE INDEX IF NOT EXISTS idx_models_type ON models(model_type)""",
    "CREATE INDEX IF NOT EXISTS idx_prompts_name ON system_prompts(name)",
    "CREATE INDEX IF NOT EXISTS idx_doc_registry_rule ON doc_registry(rule_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_registry_timestamp ON doc_registry(timestamp)",
]
