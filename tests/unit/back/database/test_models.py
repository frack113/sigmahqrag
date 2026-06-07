"""Tests for database dataclass models."""

from src.infrastructure.database.models import (
    ConfigRow,
    DocRegistryRow,
    EmbeddingConfigRow,
    GitMetadataRow,
    GitSelectedDirRow,
    ModelRow,
    PromptRow,
)


class TestPromptRow:
    def test_init_required(self) -> None:
        row = PromptRow(id="p1", name="prompt1")
        assert row.id == "p1"
        assert row.name == "prompt1"
        assert row.description == ""
        assert row.content == ""
        assert row.is_active is False

    def test_init_full(self) -> None:
        row = PromptRow(
            id="p1", name="prompt1", description="desc", content="content", is_active=True
        )
        assert row.description == "desc"
        assert row.content == "content"
        assert row.is_active is True


class TestModelRow:
    def test_init_required(self) -> None:
        row = ModelRow(repo_id="org/model", model_type="llm")
        assert row.repo_id == "org/model"
        assert row.model_type == "llm"
        assert row.status == "ready"
        assert row.file_size == 0

    def test_init_full(self) -> None:
        row = ModelRow(
            repo_id="org/m",
            model_type="embedding",
            local_path="/path",
            file_size=100,
            status="downloading",
            dimension=384,
            index_path="/idx",
            files='{"f":"v"}',
            updated_at="2024-01-01",
        )
        assert row.dimension == 384
        assert row.index_path == "/idx"


class TestDocRegistryRow:
    def test_init(self) -> None:
        row = DocRegistryRow(url_hash="abc123", original_url="https://example.com/doc")
        assert row.url_hash == "abc123"
        assert row.original_url == "https://example.com/doc"


class TestEmbeddingConfigRow:
    def test_init(self) -> None:
        row = EmbeddingConfigRow(doc_type="sigmaref")
        assert row.doc_type == "sigmaref"
        assert row.model == ""
        assert row.chunk_size == 1024

    def test_init_custom(self) -> None:
        row = EmbeddingConfigRow(doc_type="github", model="e5-small", chunk_size=512, overlap=128)
        assert row.model == "e5-small"
        assert row.chunk_size == 512
        assert row.overlap == 128


class TestGitMetadataRow:
    def test_init(self) -> None:
        row = GitMetadataRow(repo_key="org/repo", metadata='{"key": "val"}')
        assert row.repo_key == "org/repo"
        assert row.metadata == '{"key": "val"}'


class TestGitSelectedDirRow:
    def test_init(self) -> None:
        row = GitSelectedDirRow(repo_key="org/repo", dir_path="src/")
        assert row.repo_key == "org/repo"
        assert row.dir_path == "src/"


class TestConfigRow:
    def test_init(self) -> None:
        row = ConfigRow(key="llamacpp_version", value="b1234")
        assert row.key == "llamacpp_version"
        assert row.value == "b1234"
