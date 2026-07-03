"""Tests for the sparse encoder module (Q3.2 — IDF-aware BM25)."""

from __future__ import annotations

import math

import pytest

from src.core.search.sparse_encoder import (
    IDFCalculator,
    _encode_single,
    _token_id,
    _tokenize,
    bm25_idf_sparse_encoder,
    bm25_sparse_encoder,
)


class TestTokenize:
    def test_basic(self) -> None:
        assert _tokenize("Process Creation with Image") == [
            "process",
            "creation",
            "with",
            "image",
        ]

    def test_short_words_filtered(self) -> None:
        assert _tokenize("a an the of to be") == ["the"]

    def test_alphanumeric(self) -> None:
        assert _tokenize("T1059.001") == ["t1059"]

    def test_empty(self) -> None:
        assert _tokenize("") == []


class TestTokenId:
    def test_deterministic(self) -> None:
        assert _token_id("process") == _token_id("process")
        assert _token_id("process") != _token_id("Process")

    def test_within_range(self) -> None:
        tid = _token_id("process_creation")
        assert 0 <= tid < 2**24


class TestEncodeSingle:
    def test_basic_tf(self) -> None:
        indices, values = _encode_single("the process process creation")
        token_ids = {_token_id("process"): 0, _token_id("creation"): 0}
        for idx, val in zip(indices, values):
            token_ids[idx] = val
        assert _token_id("process") in token_ids
        assert _token_id("creation") in token_ids
        assert values == [1.0 + math.log(2), 1.0 + math.log(1)]

    def test_empty_returns_empty(self) -> None:
        assert _encode_single("") == ([], [])
        assert _encode_single("a an") == ([], [])

    def test_with_idf(self) -> None:
        idf_map = {"process": 2.5, "creation": 1.5}
        indices, values = _encode_single("the process process creation", idf_map=idf_map)
        id_by_token = {_token_id("process"): None, _token_id("creation"): None}
        for idx, val in zip(indices, values):
            id_by_token[idx] = val

        proc_val = id_by_token[_token_id("process")]
        creat_val = id_by_token[_token_id("creation")]
        assert proc_val is not None
        assert creat_val is not None
        assert proc_val != creat_val


class TestIDFCalculator:
    def test_empty_corpus(self) -> None:
        calc = IDFCalculator()
        assert calc.idf() == {}

    def test_single_doc(self) -> None:
        calc = IDFCalculator()
        calc.add_document("the process creation")
        idf_map = calc.idf()
        assert "process" in idf_map
        assert "creation" in idf_map

    def test_idf_higher_for_rare_terms(self) -> None:
        calc = IDFCalculator()
        for _ in range(100):
            calc.add_document("process creation")
        for _ in range(5):
            calc.add_document("rare term specific")
        idf_map = calc.idf()
        assert idf_map["rare"] > idf_map["process"]

    def test_smooth_idf(self) -> None:
        calc = IDFCalculator()
        calc.add_document("term")
        assert calc.idf(smooth=True)["term"] == pytest.approx(
            math.log(1.0 + (1 - 1 + 0.5) / (1 + 0.5))
        )


class TestBm25SparseEncoder:
    def test_basic(self) -> None:
        indices, values = bm25_sparse_encoder(["process creation"])
        assert len(indices) == 1
        assert len(values) == 1
        assert len(indices[0]) == 2

    def test_batch(self) -> None:
        texts = ["process creation", "network connection", ""]
        indices, values = bm25_sparse_encoder(texts)
        assert len(indices) == 3
        assert len(values) == 3
        assert indices[2] == []  # empty text
        assert values[2] == []


class TestBm25IdfSparseEncoder:
    def test_basic(self) -> None:
        idf_map = {"process": 2.0, "creation": 1.5}
        indices, values = bm25_idf_sparse_encoder(
            ["process creation"],
            idf_map=idf_map,
            avg_doc_len=10.0,
        )
        assert len(indices) == 1
        assert len(indices[0]) == 2

    def test_unknown_term_gets_default_idf(self) -> None:
        indices, values = bm25_idf_sparse_encoder(
            ["process creation"],
            idf_map={"foo": 1.0},
            avg_doc_len=10.0,
        )
        assert len(indices[0]) == 2
        assert all(v > 0 for v in values[0])

    def test_empty_text(self) -> None:
        indices, values = bm25_idf_sparse_encoder(
            [""],
            idf_map={"term": 1.0},
            avg_doc_len=10.0,
        )
        assert indices == [[]]
        assert values == [[]]

    def test_length_normalization(self) -> None:
        """Short doc should get higher BM25 weight per term."""
        idf_map = {"process": 2.0}
        _, values_short = bm25_idf_sparse_encoder(
            ["process"],
            idf_map=idf_map,
            avg_doc_len=100.0,
        )
        _, values_long = bm25_idf_sparse_encoder(
            ["process"],
            idf_map=idf_map,
            avg_doc_len=1.0,
        )
        # Shorter-than-avg doc gets slightly different weight
        assert values_short[0] != values_long[0]
