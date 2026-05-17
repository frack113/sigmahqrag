DDL: list[str] = [
    """CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS embedding_config (
        doc_type TEXT PRIMARY KEY,
        model TEXT NOT NULL DEFAULT '',
        chunk_size INTEGER DEFAULT 512,
        overlap INTEGER DEFAULT 50
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
    """CREATE TABLE IF NOT EXISTS doc_sigma_ref (
        url_hash TEXT PRIMARY KEY,
        original_url TEXT NOT NULL,
        normalized_url TEXT,
        content_type TEXT,
        rule_id TEXT,
        title TEXT,
        timestamp TEXT,
        content_sha256 TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS embed_progress (
        task_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending',
        total INTEGER DEFAULT 0,
        processed INTEGER DEFAULT 0,
        errors INTEGER DEFAULT 0,
        skipped INTEGER DEFAULT 0,
        current_file TEXT DEFAULT '',
        collection_name TEXT DEFAULT '',
        started_at TEXT,
        updated_at TEXT
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
    "CREATE INDEX IF NOT EXISTS idx_doc_sigma_ref_rule ON doc_sigma_ref(rule_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_sigma_ref_timestamp ON doc_sigma_ref(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_embed_progress_status ON embed_progress(status)",
]
