from dataclasses import dataclass


@dataclass
class PromptRow:
    id: str
    name: str
    description: str = ""
    content: str = ""
    is_active: bool = False


@dataclass
class ModelRow:
    repo_id: str
    model_type: str
    local_path: str | None = None
    file_size: int = 0
    status: str = "ready"
    dimension: int | None = None
    index_path: str | None = None
    files: str | None = None
    updated_at: str | None = None


@dataclass
class DocRegistryRow:
    url_hash: str
    original_url: str
    normalized_url: str | None = None
    content_type: str | None = None
    rule_id: str | None = None
    title: str | None = None
    timestamp: str | None = None
    content_sha256: str | None = None


@dataclass
class EmbeddingConfigRow:
    doc_type: str
    model: str = ""
    chunk_size: int = 1024
    overlap: int = 64


@dataclass
class GitMetadataRow:
    repo_key: str
    metadata: str


@dataclass
class GitSelectedDirRow:
    repo_key: str
    dir_path: str
    updated: str | None = None


@dataclass
class ConfigRow:
    key: str
    value: str
