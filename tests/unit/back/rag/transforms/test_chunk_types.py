"""Parametrized tests for Sigma rich-chunk types and edge cases."""

from unittest.mock import patch

import pytest

from src.rag.transforms.sigma.chunker import SigmaChunker
from src.rag.transforms.base import TransformConfig

ALL_CHUNK_TYPES = frozenset(
    {
        "executive_summary",
        "rule_metadata_lifecycle",
        "logsource_context",
        "mitre_attack_mapping",
        "detection_condition",
        "detection_selection_block",
        "detection_filter_block",
        "field_operator_group",
        "atomic_indicator",
        "indicator_inventory",
        "investigation_guidance",
        "false_positive_context",
        "natural_language_queries",
        "backend_mapping_hints",
    }
)


@pytest.fixture
def config():
    return TransformConfig()


@pytest.fixture
def full_rule_dict():
    """A maximal Sigma rule triggering every chunk type."""
    return {
        "title": "Test Full Rule",
        "id": "test-full-001",
        "description": "A comprehensive test rule",
        "level": "high",
        "status": "stable",
        "tags": ["attack.t1059", "attack.t1078", "windows"],
        "logsource": {
            "product": "windows",
            "category": "process_creation",
            "service": "security",
        },
        "detection": {
            "selection": {"Image|endswith": "powershell.exe", "CommandLine": "test"},
            "filter_main": {"EventID": 9999},
            "condition": "selection and not filter_main",
        },
        "falsepositives": ["Admin activity", "Software installers"],
        "references": ["https://example.com/test"],
        "author": "Test Author",
        "date": "2024/01/01",
        "modified": "2024/06/01",
    }


@pytest.fixture
def minimal_rule_dict():
    """A minimal Sigma rule with only required fields."""
    return {
        "title": "Minimal Rule",
        "id": "test-min-001",
        "logsource": {"product": "windows"},
        "detection": {
            "selection": {"EventID": 4688},
            "condition": "selection",
        },
    }


class TestAllChunkTypes:
    """Verify that all 14 chunk types are produced."""

    def test_all_chunk_types_present(self, config, full_rule_dict):
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(full_rule_dict)
        produced_types = {c["chunk_type"] for c in chunks}
        missing = ALL_CHUNK_TYPES - produced_types
        assert not missing, f"Missing chunk types: {missing}"

    def test_at_least_one_of_each_structural_type(self, config, full_rule_dict):
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(full_rule_dict)
        counts: dict[str, int] = {}
        for c in chunks:
            counts[c["chunk_type"]] = counts.get(c["chunk_type"], 0) + 1
        assert counts["detection_selection_block"] >= 1
        assert counts["field_operator_group"] >= 1
        assert counts["atomic_indicator"] >= 1

    def test_minimal_rule_still_has_core_chunks(self, config, minimal_rule_dict):
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(minimal_rule_dict)
        produced_types = {c["chunk_type"] for c in chunks}
        core_types = {
            "executive_summary",
            "rule_metadata_lifecycle",
            "logsource_context",
            "detection_condition",
            "detection_selection_block",
            "field_operator_group",
            "atomic_indicator",
            "indicator_inventory",
            "investigation_guidance",
            "false_positive_context",
            "natural_language_queries",
            "backend_mapping_hints",
        }
        missing = core_types - produced_types
        assert not missing, f"Minimal rule missing core chunk types: {missing}"

    @pytest.mark.parametrize("chunk_type", sorted(ALL_CHUNK_TYPES))
    def test_each_chunk_type_has_required_fields(self, config, full_rule_dict, chunk_type):
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(full_rule_dict)
        matching = [c for c in chunks if c["chunk_type"] == chunk_type]
        assert matching, f"No chunks of type {chunk_type} produced"
        for chunk in matching:
            assert "text" in chunk, f"{chunk_type} missing 'text'"
            assert "metadata" in chunk, f"{chunk_type} missing 'metadata'"


class TestEdgeCases:
    """Edge cases for Sigma rule parsing and chunking."""

    def test_empty_detection(self, config):
        rule = {
            "title": "Empty Detection",
            "id": "test-empty-det",
            "logsource": {"product": "windows"},
            "detection": {},
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        assert len(chunks) > 0
        assert all(c["chunk_type"] != "detection_selection_block" for c in chunks)

    def test_detection_with_only_condition(self, config):
        rule = {
            "title": "Condition Only",
            "id": "test-cond-only",
            "logsource": {"product": "windows"},
            "detection": {"condition": "selection"},
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        chunk_types = {c["chunk_type"] for c in chunks}
        assert "detection_condition" in chunk_types

    def test_rule_without_logsource(self, config):
        rule = {
            "title": "No Logsource",
            "id": "test-no-ls",
            "detection": {"selection": {"EventID": 1}, "condition": "selection"},
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        logsource_chunks = [c for c in chunks if c["chunk_type"] == "logsource_context"]
        assert len(logsource_chunks) == 1
        assert "unknown" in logsource_chunks[0]["text"]

    def test_rule_without_tags(self, config):
        rule = {
            "title": "No Tags",
            "id": "test-no-tags",
            "logsource": {"product": "windows"},
            "detection": {"selection": {"EventID": 1}, "condition": "selection"},
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        attack_chunks = [c for c in chunks if c["chunk_type"] == "mitre_attack_mapping"]
        assert len(attack_chunks) == 0

    def test_rule_with_duplicate_ids(self, config):
        rule1 = {
            "title": "Duplicate ID A",
            "id": "test-dup",
            "logsource": {"product": "windows"},
            "detection": {"selection": {"EventID": 1}, "condition": "selection"},
        }
        rule2 = {
            "title": "Duplicate ID B",
            "id": "test-dup",
            "logsource": {"product": "linux"},
            "detection": {"selection": {"EventID": 2}, "condition": "selection"},
        }
        chunker = SigmaChunker(config=config)
        chunks1 = chunker._chunk_rule(rule1)
        chunks2 = chunker._chunk_rule(rule2)
        ids1 = {c.get("metadata", {}).get("rule_id") for c in chunks1}
        ids2 = {c.get("metadata", {}).get("rule_id") for c in chunks2}
        assert "test-dup" in ids1
        assert "test-dup" in ids2
        assert len(chunks1) > 0
        assert len(chunks2) > 0

    def test_filter_blocks_marked_correctly(self, config):
        rule = {
            "title": "Filter Test",
            "id": "test-filter",
            "logsource": {"product": "windows"},
            "detection": {
                "selection": {"EventID": 4688},
                "filter_main": {"EventID": 9999},
                "filter_admin": {"UserName": "admin"},
                "condition": "selection and not filter_main",
            },
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        selection_chunks = [c for c in chunks if c["chunk_type"] == "detection_selection_block"]
        filter_chunks = [c for c in chunks if c["chunk_type"] == "detection_filter_block"]
        assert len(selection_chunks) >= 1
        assert len(filter_chunks) >= 1
        for fc in filter_chunks:
            meta = fc.get("metadata", {})
            assert meta.get("is_filter") is True

    def test_sigma_modifiers_preserved(self, config):
        rule = {
            "title": "Modifier Test",
            "id": "test-mod",
            "logsource": {"product": "windows"},
            "detection": {
                "selection": {
                    "Image|endswith": ".exe",
                    "CommandLine|contains": "suspicious",
                    "ParentImage|startswith": "C:\\Windows",
                },
                "condition": "selection",
            },
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        atomic_values = []
        for c in chunks:
            if c["chunk_type"] == "atomic_indicator":
                atomic_values.append(c.get("metadata", {}).get("operator", ""))
        assert "endswith" in atomic_values or "endswith" in str([c["text"] for c in chunks])
        assert "contains" in atomic_values or "contains" in str([c["text"] for c in chunks])

    def test_very_large_falsepositives_list(self, config):
        rule = {
            "title": "Many FPs",
            "id": "test-fps",
            "logsource": {"product": "windows"},
            "detection": {"selection": {"EventID": 1}, "condition": "selection"},
            "falsepositives": [f"FP {i}" for i in range(100)],
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        fp_chunks = [c for c in chunks if c["chunk_type"] == "false_positive_context"]
        assert len(fp_chunks) == 1
        assert "FP 99" in fp_chunks[0]["text"]

    def test_rule_without_id(self, config):
        rule = {
            "title": "No ID",
            "logsource": {"product": "windows"},
            "detection": {"selection": {"EventID": 1}, "condition": "selection"},
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        assert len(chunks) > 0

    def test_re_modifier_preserved(self, config):
        rule = {
            "title": "Regex Modifier Test",
            "id": "test-re",
            "logsource": {"product": "windows"},
            "detection": {
                "selection": {
                    "CommandLine|re": ".*suspicious.*",
                    "Image|re": ".*\\\\powershell\\.exe$",
                },
                "condition": "selection",
            },
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        atomic_ops = [
            c.get("metadata", {}).get("operator", "")
            for c in chunks
            if c["chunk_type"] == "atomic_indicator"
        ]
        assert "re" in atomic_ops

    def test_all_modifier_preserved(self, config):
        rule = {
            "title": "All Modifier Test",
            "id": "test-all",
            "logsource": {"product": "windows"},
            "detection": {
                "selection": {
                    "CommandLine|contains|all": [".exe", ".dll", ".ps1"],
                },
                "condition": "selection",
            },
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        atomic_ops = [
            c.get("metadata", {}).get("operator", "")
            for c in chunks
            if c["chunk_type"] == "atomic_indicator"
        ]
        assert any("all" in op for op in atomic_ops)

    def test_base64_modifier_preserved(self, config):
        rule = {
            "title": "Base64 Modifier Test",
            "id": "test-b64",
            "logsource": {"product": "windows"},
            "detection": {
                "selection": {
                    "CommandLine|base64": "JABzAHkAcwB0AGUAbQAgAHAAcgBvAHgAeQAgAHMAaQB0AGUA",
                },
                "condition": "selection",
            },
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        fields = [
            c.get("metadata", {}).get("field", "")
            for c in chunks
            if c["chunk_type"] == "field_operator_group"
        ]
        assert any("CommandLine" in f for f in fields)

    def test_rule_without_title(self, config):
        rule: dict = {
            "id": "test-no-title",
            "logsource": {"product": "windows"},
            "detection": {"selection": {"EventID": 4688}, "condition": "selection"},
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        assert len(chunks) > 0
        texts = [c.get("text", "") for c in chunks]
        assert any("Untitled Sigma rule" in t for t in texts)

    def test_rule_with_nested_detection_values(self, config):
        rule = {
            "title": "Nested Detection",
            "id": "test-nested",
            "logsource": {"product": "windows"},
            "detection": {
                "selection1": {"Image": "powershell.exe"},
                "selection2": {"CommandLine": "sus.exe"},
                "condition": "selection1 or selection2",
            },
        }
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(rule)
        selection_chunks = [c for c in chunks if c["chunk_type"] == "detection_selection_block"]
        type_names = {c.get("metadata", {}).get("detection_name") for c in selection_chunks}
        assert "selection1" in type_names
        assert "selection2" in type_names


class TestLLMEnrichment:
    """Tests for LLM-based enrichment of Sigma chunks."""

    def test_enrichment_applied_when_llm_client_provided(self, full_rule_dict):
        """Chunks should contain Summary/Keywords when LLM client is available."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        # Mock _extract_keywords to return predictable results
        with (
            patch(
                "src.rag.transforms.sigma.chunker._extract_keywords",
                return_value=("Test summary", "keyword1, keyword2, keyword3"),
            ),
            patch(
                "src.rag.transforms.sigma.chunker._get_llm_client",
                return_value=mock_client,
            ),
        ):
            config = TransformConfig(enable_llm_enrichment=True)
            chunker = SigmaChunker(config=config)
            chunks = chunker._chunk_rule(full_rule_dict, llm_client=mock_client)

        assert len(chunks) > 0
        for chunk in chunks:
            text = chunk["text"]
            assert "---" in text, f"Chunk {chunk['chunk_type']} missing enrichment separator"
            assert "Summary: Test summary" in text, f"Chunk {chunk['chunk_type']} missing summary"
            assert "Keywords: keyword1, keyword2, keyword3" in text, (
                f"Chunk {chunk['chunk_type']} missing keywords"
            )

    def test_no_enrichment_when_llm_client_none(self, full_rule_dict):
        """Chunks should NOT contain enrichment when no LLM client is provided."""
        config = TransformConfig()
        chunker = SigmaChunker(config=config)
        chunks = chunker._chunk_rule(full_rule_dict, llm_client=None)

        assert len(chunks) > 0
        for chunk in chunks:
            text = chunk["text"]
            assert "Summary:" not in text, (
                f"Chunk {chunk['chunk_type']} unexpectedly has enrichment"
            )

    def test_enrichment_failure_does_not_break_chunking(self, full_rule_dict):
        """Chunking should succeed even if LLM enrichment fails."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        with patch(
            "src.rag.transforms.sigma.chunker._extract_keywords",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            config = TransformConfig(enable_llm_enrichment=True)
            chunker = SigmaChunker(config=config)
            chunks = chunker._chunk_rule(full_rule_dict, llm_client=mock_client)

        assert len(chunks) > 0
        # Chunks should still have their original text (no enrichment appended)
        for chunk in chunks:
            assert "Summary:" not in chunk["text"]

    def test_enrichment_empty_result_preserves_original_text(self, full_rule_dict):
        """When LLM returns empty summary+keywords, original text is preserved."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        with patch(
            "src.rag.transforms.sigma.chunker._extract_keywords",
            return_value=("", ""),
        ):
            config = TransformConfig(enable_llm_enrichment=True)
            chunker = SigmaChunker(config=config)
            chunks = chunker._chunk_rule(full_rule_dict, llm_client=mock_client)

        assert len(chunks) > 0
        for chunk in chunks:
            assert "---" not in chunk["text"], (
                f"Chunk {chunk['chunk_type']} has enrichment separator with empty result"
            )

    def test_enrichment_called_for_all_chunks(self, full_rule_dict):
        """_extract_keywords should be called once per chunk."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        with patch(
            "src.rag.transforms.sigma.chunker._extract_keywords",
            return_value=("summary", "keywords"),
        ) as mock_extract:
            config = TransformConfig(enable_llm_enrichment=True)
            chunker = SigmaChunker(config=config)
            chunks = chunker._chunk_rule(full_rule_dict, llm_client=mock_client)

        assert mock_extract.call_count == len(chunks)
