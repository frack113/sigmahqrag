"""Tests for document transforms package."""

import pytest

from src.rag.transforms.base import DocumentTransform, TransformConfig
from src.rag.transforms.registry import TransformRegistry
from src.rag.transforms.sigma.parser import SigmaParser
from src.rag.transforms.sigma.chunker import SigmaChunker


@pytest.fixture
def sample_sigma_file(tmp_path):
    """Create a minimal Sigma rule YAML file for testing."""
    rule_yaml = """
title: Test Sigma Rule
id: 12345678-1234-1234-1234-123456789012
status: test
description: Tests a suspicious process
author: Test Author
date: 2024/01/01
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        CommandLine|endswith: '.exe'
    condition: selection
"""
    test_file = tmp_path / "test_rule.yml"
    test_file.write_text(rule_yaml)
    return test_file


class TestTransformConfig:
    """Tests for TransformConfig dataclass."""

    def test_default_config(self):
        config = TransformConfig()
        assert config.collection_name == "default"
        assert config.model_name == "intfloat/multilingual-e5-small"
        assert config.chunk_size == 1024
        assert config.chunk_overlap == 100
        assert config.batch_size == 8
        assert config.max_length == 512
        assert config.enable_sbert is True
        assert config.enable_rich_chunks is False
        assert config.enable_eval_questions is False

    def test_custom_config(self):
        config = TransformConfig(
            collection_name="test_collection",
            model_name="test-model",
            chunk_size=512,
            enable_rich_chunks=True,
        )
        assert config.collection_name == "test_collection"
        assert config.model_name == "test-model"
        assert config.chunk_size == 512
        assert config.enable_rich_chunks is True


class TestDocumentTransform:
    """Tests for DocumentTransform base class."""

    def test_build_default_config(self):
        # Should work without error (may need env vars)
        config = SigmaParser._build_default_config()
        assert isinstance(config, TransformConfig)
        assert config.collection_name is not None
        # Verify it uses Config (not RAGConfig which doesn't exist)
        assert config.collection_name in ("default", "sigmaref", "sigma_docs")

    def test_can_handle_with_extension(self):
        assert SigmaParser.can_handle("test.yml")
        assert SigmaParser.can_handle("test.yaml")
        assert not SigmaParser.can_handle("test.pdf")

    def test_can_handle_with_path(self, tmp_path):
        yml_file = tmp_path / "test.yml"
        yml_file.touch()
        assert SigmaParser.can_handle(yml_file)


class TestTransformRegistry:
    """Tests for TransformRegistry."""

    def test_register_and_get(self):
        class MockTransform(DocumentTransform):
            FORMAT_NAME = "mock_format"
            SUPPORTED_EXTENSIONS = (".mock",)

            def parse(self, file_path):
                return []

            def chunk(self, documents):
                return documents

        TransformRegistry.register(MockTransform)

        result = TransformRegistry.get("mock_format")
        assert result is MockTransform

    def test_get_returns_none_for_unknown(self):
        result = TransformRegistry.get("unknown_format")
        assert result is None

    def test_find_for_file(self, sample_sigma_file):
        # Should find SigmaParser for .yml files
        result = TransformRegistry.find_for_file(sample_sigma_file)
        assert result is not None
        assert result.FORMAT_NAME == "sigma_rules"

    def test_register_all(self):
        class Transform1(DocumentTransform):
            FORMAT_NAME = "format1"
            SUPPORTED_EXTENSIONS = (".f1",)

            def parse(self, file_path):
                return []

            def chunk(self, documents):
                return documents

        class Transform2(DocumentTransform):
            FORMAT_NAME = "format2"
            SUPPORTED_EXTENSIONS = (".f2",)

            def parse(self, file_path):
                return []

            def chunk(self, documents):
                return documents

        TransformRegistry.register_all(Transform1, Transform2)

        assert TransformRegistry.get("format1") is Transform1
        assert TransformRegistry.get("format2") is Transform2

    def test_list_formats(self):
        formats = TransformRegistry.list_formats()
        assert "sigma_rules" in formats


class TestSigmaParser:
    """Tests for SigmaParser transform."""

    def test_parse_flat_mode(self, sample_sigma_file):
        config = TransformConfig(enable_rich_chunks=False)
        parser = SigmaParser(config)

        documents = parser.parse(sample_sigma_file)

        assert len(documents) == 1
        doc = documents[0]
        assert doc.text is not None
        assert "Test Sigma Rule" in doc.text
        assert "process_creation" in doc.text
        assert doc.metadata["rule_id"] == "12345678-1234-1234-1234-123456789012"

    def test_parse_multiple_rules(self, tmp_path):
        """Test parsing a file with multiple rules."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()

        for i in range(3):
            content = f"""
title: Rule {i}
id: id-{i}
status: test
logsource:
    category: process_creation
detection:
    selection:
        CommandLine|endswith: '.exe'
    condition: selection
"""
            rule_file = rules_dir / f"rule_{i}.yml"
            rule_file.write_text(content)

        config = TransformConfig(enable_rich_chunks=False)
        parser = SigmaParser(config)

        all_docs = []
        for rule_file in rules_dir.iterdir():
            docs = parser.parse(rule_file)
            all_docs.extend(docs)

        assert len(all_docs) == 3

    def test_parse_empty_file(self, tmp_path):
        """Test parsing an empty YAML file."""
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")

        config = TransformConfig(enable_rich_chunks=False)
        parser = SigmaParser(config)

        documents = parser.parse(empty_file)
        assert len(documents) == 0

    def test_chunk_flat_mode(self, sample_sigma_file):
        """Test that chunk() returns documents unchanged in flat mode."""
        config = TransformConfig(enable_rich_chunks=False)
        parser = SigmaParser(config)

        documents = parser.parse(sample_sigma_file)
        chunks = parser.chunk(documents)

        assert len(chunks) == len(documents)


class TestSigmaChunker:
    """Tests for SigmaChunker transform."""

    def test_parse_rich_mode(self, sample_sigma_file):
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config)

        documents = chunker.parse(sample_sigma_file)

        assert len(documents) == 1
        doc = documents[0]
        assert doc.text == ""  # Rich mode: text is empty, chunks created later
        assert doc.metadata["rule_id"] == "12345678-1234-1234-1234-123456789012"

    def test_chunk_rich_mode(self, sample_sigma_file):
        """Test that rich chunking produces multiple chunks."""
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config)

        documents = chunker.parse(sample_sigma_file)
        chunks = chunker.chunk(documents)

        # Should produce multiple chunks per rule
        assert len(chunks) > 1

        # Check chunk types
        chunk_types = [doc.metadata.get("chunk_type") for doc in chunks]
        assert "executive_summary" in chunk_types
        assert "logsource_context" in chunk_types
        assert "detection_condition" in chunk_types

    def test_run_rich_mode(self, sample_sigma_file):
        """Test full run (parse + chunk + post_process) in rich mode."""
        config = TransformConfig(
            enable_rich_chunks=True,
            enable_eval_questions=True,
        )
        chunker = SigmaChunker(config)

        result = chunker.run(sample_sigma_file)

        assert len(result) > 1
        assert all(isinstance(doc, type(result[0])) for doc in result)

    def test_chunk_metadata_preserved(self, sample_sigma_file):
        """Test that metadata is preserved through chunking."""
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config)

        documents = chunker.parse(sample_sigma_file)
        chunks = chunker.chunk(documents)

        assert chunks[0].metadata.get("rule_id") == "12345678-1234-1234-1234-123456789012"
        assert "chunk_type" in chunks[0].metadata
