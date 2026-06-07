"""Tests for document transforms package."""

import pytest

from src.core.base import DocumentTransform, TransformConfig
from src.core.registry import TransformRegistry
from src.core.sigma.parser import SigmaParser
from src.core.sigma.chunker import SigmaChunker


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
        assert config.enable_eval_questions is False

    def test_custom_config(self):
        config = TransformConfig(
            collection_name="test_collection",
            model_name="test-model",
            chunk_size=512,
        )
        assert config.collection_name == "test_collection"
        assert config.model_name == "test-model"
        assert config.chunk_size == 512


class TestDocumentTransform:
    """Tests for DocumentTransform base class."""

    def test_build_default_config(self):
        config = SigmaParser._build_default_config()
        assert isinstance(config, TransformConfig)
        assert config.collection_name is not None

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

            def process(self, documents):
                return documents

        TransformRegistry.register(MockTransform)
        result = TransformRegistry.get("mock_format")
        assert result is MockTransform

    def test_get_returns_none_for_unknown(self):
        result = TransformRegistry.get("unknown_format")
        assert result is None

    def test_find_for_file_finds_sigma_chunker(self, sample_sigma_file):
        result = TransformRegistry.find_for_file(sample_sigma_file)
        assert result is not None
        assert result is SigmaChunker
        assert result.FORMAT_NAME == "sigma"

    def test_register_all(self):
        class Transform1(DocumentTransform):
            FORMAT_NAME = "format1"
            SUPPORTED_EXTENSIONS = (".f1",)

            def parse(self, file_path):
                return []

            def process(self, documents):
                return documents

        class Transform2(DocumentTransform):
            FORMAT_NAME = "format2"
            SUPPORTED_EXTENSIONS = (".f2",)

            def parse(self, file_path):
                return []

            def process(self, documents):
                return documents

        TransformRegistry.register_all(Transform1, Transform2)
        assert TransformRegistry.get("format1") is Transform1
        assert TransformRegistry.get("format2") is Transform2

    def test_list_formats_includes_sigma(self):
        formats = TransformRegistry.list_formats()
        assert "sigma" in formats


class TestSigmaParser:
    """Tests for SigmaParser transform (parse-only)."""

    def test_parse_emits_empty_text_with_rule_meta(self, sample_sigma_file):
        config = TransformConfig()
        parser = SigmaParser(config)

        documents = parser.parse(sample_sigma_file)

        assert len(documents) == 1
        doc = documents[0]
        assert doc.text == ""
        assert doc.metadata["rule_id"] == "12345678-1234-1234-1234-123456789012"
        assert "rule_meta" in doc.metadata
        assert doc.metadata["rule_meta"]["title"] == "Test Sigma Rule"
        assert doc.metadata["doc_type"] == "sigma_rule"
        assert doc.metadata["file_name"] == "test_rule.yml"

    def test_parse_multiple_rules(self, tmp_path):
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

        config = TransformConfig()
        parser = SigmaParser(config)

        all_docs = []
        for rule_file in rules_dir.iterdir():
            docs = parser.parse(rule_file)
            all_docs.extend(docs)

        assert len(all_docs) == 3

    def test_parse_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")

        config = TransformConfig()
        parser = SigmaParser(config)

        documents = parser.parse(empty_file)
        assert len(documents) == 0

    def test_process_raises_not_implemented(self, sample_sigma_file):
        config = TransformConfig()
        parser = SigmaParser(config)
        documents = parser.parse(sample_sigma_file)

        with pytest.raises(NotImplementedError):
            parser.process(documents)


class TestSigmaChunker:
    """Tests for SigmaChunker transform."""

    def test_parse_emits_empty_text_with_rule_meta(self, sample_sigma_file):
        config = TransformConfig()
        chunker = SigmaChunker(config)

        documents = chunker.parse(sample_sigma_file)

        assert len(documents) == 1
        doc = documents[0]
        assert doc.text == ""
        assert doc.metadata["rule_id"] == "12345678-1234-1234-1234-123456789012"
        assert "rule_meta" in doc.metadata

    def test_process_produces_multiple_chunks(self, sample_sigma_file):
        config = TransformConfig()
        chunker = SigmaChunker(config)

        documents = chunker.parse(sample_sigma_file)
        chunks = chunker.process(documents)

        assert len(chunks) > 1

        chunk_types = [doc.metadata.get("chunk_type") for doc in chunks]
        assert "executive_summary" in chunk_types
        assert "logsource_context" in chunk_types
        assert "detection_condition" in chunk_types

    def test_run_full_pipeline(self, sample_sigma_file):
        config = TransformConfig(enable_eval_questions=True)
        chunker = SigmaChunker(config)

        result = chunker.run(sample_sigma_file)

        assert len(result) > 1
        assert all(isinstance(doc, type(result[0])) for doc in result)
        for doc in result:
            assert doc.metadata.get("collection") == "default"

    def test_process_metadata_preserved(self, sample_sigma_file):
        config = TransformConfig()
        chunker = SigmaChunker(config)

        documents = chunker.parse(sample_sigma_file)
        chunks = chunker.process(documents)

        assert chunks[0].metadata.get("rule_id") == "12345678-1234-1234-1234-123456789012"
        assert "chunk_type" in chunks[0].metadata


class TestCollectionInjection:
    """Tests that DocumentTransform.run() injects collection into metadata."""

    def test_run_injects_collection_with_sigma_chunker(self, sample_sigma_file):
        config = TransformConfig(collection="sigma_rules")
        chunker = SigmaChunker(config)
        result = chunker.run(sample_sigma_file)

        assert len(result) > 0
        for doc in result:
            assert doc.metadata.get("collection") == "sigma_rules"

    def test_default_collection_when_not_set(self, sample_sigma_file):
        config = TransformConfig()
        chunker = SigmaChunker(config)
        result = chunker.run(sample_sigma_file)

        for doc in result:
            assert doc.metadata.get("collection") == "default"
