"""Tests for the golden set module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.search.eval.golden_set import (
    GoldenQuery,
    GoldenSet,
    create_sample_golden_set,
    load_golden_set,
    save_golden_set,
)


class TestGoldenQuery:
    def test_to_dict_roundtrip(self) -> None:
        q = GoldenQuery(
            id="q001",
            query="test query",
            collection="sigma_rules",
            relevant_doc_ids=["doc1", "doc2"],
            k=10,
        )
        d = q.to_dict()
        q2 = GoldenQuery.from_dict(d)
        assert q2.id == q.id
        assert q2.query == q.query
        assert q2.collection == q.collection
        assert q2.relevant_doc_ids == q.relevant_doc_ids
        assert q2.k == q.k

    def test_default_k(self) -> None:
        q = GoldenQuery(
            id="q001",
            query="test",
            collection="sigma_rules",
            relevant_doc_ids=["doc1"],
        )
        assert q.k == 10

    def test_from_dict_missing_k_defaults(self) -> None:
        d = {
            "id": "q001",
            "query": "test",
            "collection": "sigma_rules",
            "relevant_doc_ids": ["doc1"],
        }
        q = GoldenQuery.from_dict(d)
        assert q.k == 10


class TestGoldenSet:
    def test_add_query(self) -> None:
        gs = GoldenSet(description="test")
        q = gs.add("query", "sigma_rules", ["doc1", "doc2"], k=5)
        assert len(gs) == 1
        assert q.id == "q0000"
        assert q.query == "query"

    def test_add_query_custom_id(self) -> None:
        gs = GoldenSet()
        q = gs.add("query", "sigma_rules", ["doc1"], query_id="custom-id")
        assert q.id == "custom-id"

    def test_to_dict_roundtrip(self) -> None:
        gs = GoldenSet(description="test set")
        gs.add("q1", "sigma_rules", ["d1"])
        gs.add("q2", "sigma_docs", ["d2", "d3"], k=20)
        d = gs.to_dict()
        gs2 = GoldenSet.from_dict(d)
        assert gs2.description == "test set"
        assert len(gs2) == 2
        assert gs2.queries[0].query == "q1"
        assert gs2.queries[1].k == 20

    def test_empty_set(self) -> None:
        gs = GoldenSet()
        assert len(gs) == 0
        d = gs.to_dict()
        assert d["metadata"]["num_queries"] == 0
        assert d["queries"] == []


class TestSaveLoadGoldenSet:
    def test_save_and_load(self, tmp_path: Path) -> None:
        gs = GoldenSet(description="roundtrip test")
        gs.add("test query", "sigma_rules", ["doc1", "doc2"])
        path = save_golden_set(gs, tmp_path / "golden.json")
        assert path.exists()

        loaded = load_golden_set(path)
        assert loaded.description == "roundtrip test"
        assert len(loaded) == 1
        assert loaded.queries[0].query == "test query"

    def test_load_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_golden_set("/nonexistent/path/golden.json")

    def test_load_invalid_structure_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text(json.dumps({"not_queries": []}))
        with pytest.raises(ValueError, match="missing 'queries' key"):
            load_golden_set(bad_file)

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        gs = GoldenSet(description="nested")
        gs.add("q", "sigma_rules", ["d1"])
        path = save_golden_set(gs, tmp_path / "a" / "b" / "golden.json")
        assert path.exists()


class TestCreateSampleGoldenSet:
    def test_sample_has_queries(self) -> None:
        gs = create_sample_golden_set()
        assert len(gs) == 4
        assert gs.queries[0].collection == "sigma_rules"
        assert gs.queries[1].collection == "sigma_rules"
        assert gs.queries[2].collection == "sigma_docs"
        assert gs.queries[3].collection == "sigma_spec"
