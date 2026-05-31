"""Integration test: full RAG pipeline flow (ingest → format → LLM prompt)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from src.back.rag.search import format_search_result, get_citation
from src.back.rag.transforms.base import TransformConfig
from src.back.rag.transforms.sigma.chunker import SigmaChunker
from src.back.rag.transforms.sigma.parser import SigmaParser


@pytest.fixture
def sample_sigma_yaml(tmp_path: Path) -> Path:
    """Write a realistic Sigma rule to a temp file."""
    content = {
        "title": "Suspicious PowerShell Execution",
        "id": "test-integration-001",
        "status": "stable",
        "description": "Detects suspicious PowerShell invocation",
        "author": "Test Author",
        "date": "2024/01/01",
        "logsource": {
            "category": "process_creation",
            "product": "windows",
        },
        "detection": {
            "selection": {
                "Image|endswith": "powershell.exe",
                "CommandLine|contains": "EncodedCommand",
            },
            "filter_main": {"EventID": 9999},
            "condition": "selection and not filter_main",
        },
        "falsepositives": ["Admin scripts"],
        "level": "high",
        "tags": ["attack.t1059", "attack.t1086"],
        "references": ["https://attack.mitre.org/techniques/T1059/"],
    }
    file_path = tmp_path / "test_rule.yml"
    file_path.write_text(yaml.dump(content, default_flow_style=False), encoding="utf-8")
    return file_path


class TestFullPipelineContract:
    """Test the full document processing pipeline end-to-end."""

    def test_parse_to_search_result_flow(self, sample_sigma_yaml: Path):
        """Verify: Sigma YAML → parsed → chunked → formatted as search result.

        This validates that documents produced by the transform system have
        the metadata shape expected by RAGPipeline._format_search_results().
        """
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config=config)

        documents = chunker.parse(sample_sigma_yaml)
        assert len(documents) == 1
        assert documents[0].metadata["rule_id"] == "test-integration-001"

        chunks = chunker.chunk(documents)
        assert len(chunks) > 1

        rich_chunk = None
        for doc in chunks:
            if doc.metadata.get("chunk_type") == "executive_summary":
                rich_chunk = doc
                break
        assert rich_chunk is not None, "Missing executive_summary chunk"
        assert "powershell" in rich_chunk.text.lower()

        # The metadata shape must be compatible with RAGPipeline._format_search_results()
        meta = rich_chunk.metadata
        assert "rule_id" in meta
        assert "title" in meta
        assert "chunk_type" in meta
        assert meta["rule_id"] == "test-integration-001"

    def test_chunk_metadata_in_search_result_format(self, sample_sigma_yaml: Path):
        """Verify chunk metadata survives being wrapped in a search result dict."""
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config=config)
        documents = chunker.parse(sample_sigma_yaml)
        chunks = chunker.chunk(documents)

        for chunk in chunks:
            search_result = {
                "text": chunk.text,
                "score": 0.95,
                "metadata": chunk.metadata,
            }
            formatted = format_search_result(search_result)
            assert formatted["text"] == chunk.text
            assert formatted["score"] == 0.95
            assert formatted["metadata"]["rule_id"] == "test-integration-001"

    def test_citation_format_consistency(self, sample_sigma_yaml: Path):
        """Verify citations work across the chunk types."""
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config=config)
        documents = chunker.parse(sample_sigma_yaml)
        chunks = chunker.chunk(documents)

        for chunk in chunks:
            result = {
                "text": chunk.text,
                "score": 0.9,
                "metadata": chunk.metadata,
            }
            citation = get_citation(result)
            assert isinstance(citation, str)

    def test_flat_mode_compatible_with_search(self, sample_sigma_yaml: Path):
        """Verify flat-mode documents also produce searchable results."""
        config = TransformConfig(enable_rich_chunks=False)
        parser = SigmaParser(config=config)

        documents = parser.parse(sample_sigma_yaml)
        assert len(documents) == 1

        doc = documents[0]
        assert "powershell" in doc.text.lower()
        assert doc.metadata["rule_id"] == "test-integration-001"

        search_result = {
            "text": doc.text,
            "score": 0.85,
            "metadata": doc.metadata,
        }
        formatted = format_search_result(search_result)
        assert formatted["text"] == doc.text
        assert formatted["metadata"]["rule_id"] == "test-integration-001"

    def test_multiple_rules_in_directory(self, tmp_path: Path):
        """Verify batch processing across multiple files."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        for i in range(3):
            rule = {
                "title": f"Rule {i}",
                "id": f"test-multi-{i:03d}",
                "logsource": {"product": "windows", "category": "process_creation"},
                "detection": {"selection": {"EventID": 1000 + i}, "condition": "selection"},
            }
            (rules_dir / f"rule_{i}.yml").write_text(
                yaml.dump(rule, default_flow_style=False), encoding="utf-8"
            )

        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config=config)

        all_chunks: list[dict[str, Any]] = []
        for rule_file in rules_dir.iterdir():
            docs = chunker.parse(rule_file)
            chunks = chunker.chunk(docs)
            for c in chunks:
                all_chunks.append(
                    {
                        "text": c.text,
                        "score": 0.9,
                        "metadata": c.metadata,
                    }
                )

        assert len(all_chunks) >= 3
        rule_ids = {r["metadata"]["rule_id"] for r in all_chunks}
        assert "test-multi-000" in rule_ids
        assert "test-multi-001" in rule_ids
        assert "test-multi-002" in rule_ids

    def test_rich_chunks_preserve_attack_tags(self, sample_sigma_yaml: Path):
        """Verify ATT&CK tags survive into the chunk metadata."""
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config=config)
        documents = chunker.parse(sample_sigma_yaml)
        chunks = chunker.chunk(documents)

        attack_chunks = [
            c for c in chunks if c.metadata.get("chunk_type") == "mitre_attack_mapping"
        ]
        assert len(attack_chunks) >= 1

        meta = attack_chunks[0].metadata
        tags = meta.get("tags", [])
        attack_tags = [t for t in tags if str(t).startswith("attack.")]
        assert any("t1059" in str(t) for t in attack_tags)

    def test_prompt_template_renders_with_search_results(self):
        """Verify the Jinja2 prompt template can render with search results."""
        from jinja2 import Template

        template_str = """Based on the following Sigma rules:

{% for result in search_results %}
---
{{ result.header }}
---
{{ result.text }}
{% endfor %}

Question: {{ question }}"""

        template = Template(template_str)
        search_results = [
            {
                "header": "Rule: Suspicious PowerShell Execution | Rule ID: test-001",
                "text": "Sigma rule for detecting PowerShell abuse",
            },
            {
                "header": "Rule: Network Scan Detection | Rule ID: test-002",
                "text": "Detects network scanning activity",
            },
        ]
        rendered = template.render(
            search_results=search_results,
            question="What rules match my query?",
        )
        assert "Suspicious PowerShell Execution" in rendered
        assert "test-001" in rendered
        assert "What rules match" in rendered
