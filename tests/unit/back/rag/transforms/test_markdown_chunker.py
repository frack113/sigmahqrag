"""Tests for MarkdownChunker transform."""

from pathlib import Path

import pytest

from src.core.base import TransformConfig
from src.core.document.chunker import MarkdownChunker


SAMPLE_MD = """# Chapter 1

Introduction text for chapter one.

## Section 1.1

Details about section 1.1.

### Sub-section 1.1.1

Very specific details.

## Section 1.2

Details about section 1.2.

# Chapter 2

Introduction to chapter two.

## Section 2.1

Details about section 2.1.
"""


@pytest.fixture
def md_file(tmp_path: Path) -> Path:
    f = tmp_path / "test.md"
    f.write_text(SAMPLE_MD)
    return f


class TestMarkdownChunker:
    def test_parse(self, md_file: Path):
        chunker = MarkdownChunker(TransformConfig())
        docs = chunker.parse(md_file)
        assert len(docs) == 1
        assert docs[0].metadata["doc_type"] == "markdown"
        assert "Chapter 1" in docs[0].text

    def test_chunk_global_only_when_no_headings(self, tmp_path: Path):
        f = tmp_path / "plain.md"
        f.write_text("Just text.")
        chunker = MarkdownChunker(TransformConfig(max_heading_level=2))
        docs = chunker.parse(f)
        chunks = chunker.process(docs)
        assert len(chunks) == 1
        assert chunks[0].metadata["chunk_type"] == "global"

    def test_chunk_h1_default_level2(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        chunk_types = [c.metadata["chunk_type"] for c in chunks]
        assert "global" in chunk_types
        assert "heading_h1" in chunk_types
        assert "heading_h2" in chunk_types
        assert "heading_h3" not in chunk_types

    def test_chunk_h3_when_level3(self, md_file: Path):
        config = TransformConfig(max_heading_level=3)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        chunk_types = [c.metadata["chunk_type"] for c in chunks]
        assert "heading_h3" in chunk_types

    def test_chunk_h1_only_when_level1(self, md_file: Path):
        config = TransformConfig(max_heading_level=1)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        chunk_types = [c.metadata["chunk_type"] for c in chunks]
        assert "heading_h1" in chunk_types
        assert "heading_h2" not in chunk_types
        assert "heading_h3" not in chunk_types

    def test_heading_path_breadcrumb(self, md_file: Path):
        config = TransformConfig(max_heading_level=3)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        h3_chunks = [c for c in chunks if c.metadata["chunk_type"] == "heading_h3"]
        assert len(h3_chunks) == 1
        assert (
            h3_chunks[0].metadata["heading_path"] == "Chapter 1 > Section 1.1 > Sub-section 1.1.1"
        )

    def test_h1_chunk_includes_children(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        h1 = [
            c
            for c in chunks
            if c.metadata["chunk_type"] == "heading_h1"
            and c.metadata["heading_text"] == "Chapter 1"
        ]
        assert len(h1) == 1
        assert "Introduction text" in h1[0].text
        assert "Section 1.1" in h1[0].text
        assert "Sub-section 1.1.1" in h1[0].text
        assert "Section 1.2" in h1[0].text
        assert "Chapter 2" not in h1[0].text

    def test_h2_chunk_excludes_neighbour(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        s11 = [
            c
            for c in chunks
            if c.metadata["chunk_type"] == "heading_h2"
            and c.metadata["heading_text"] == "Section 1.1"
        ]
        assert len(s11) == 1
        assert "Details about section 1.1" in s11[0].text
        assert "Sub-section 1.1.1" in s11[0].text
        assert "Section 1.2" not in s11[0].text

    def test_metadata_preserved(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        for c in chunks:
            assert c.metadata["source_file"] == str(md_file)
            assert c.metadata["doc_type"] == "markdown"

    def test_run_full_pipeline(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        result = chunker.run(md_file)
        # global + 2 H1 + 2 H2 = 5
        assert len(result) >= 5
        assert all(isinstance(d, type(result[0])) for d in result)

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.md"
        f.write_text("")
        chunker = MarkdownChunker(TransformConfig(max_heading_level=2))
        docs = chunker.parse(f)
        chunks = chunker.process(docs)
        assert len(chunks) == 1

    def test_can_handle(self):
        assert MarkdownChunker.can_handle("readme.md")
        assert MarkdownChunker.can_handle("CHANGELOG.markdown")
        assert not MarkdownChunker.can_handle("notes.txt")
        assert not MarkdownChunker.can_handle("doc.pdf")

    def test_chunk_count_level1(self, md_file: Path):
        config = TransformConfig(max_heading_level=1)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        # global + 2 H1 = 3
        assert len(chunks) == 3

    def test_chunk_count_level2(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        # global + 2 H1 + 3 H2 = 6
        assert len(chunks) == 6

    def test_chunk_count_level3(self, md_file: Path):
        config = TransformConfig(max_heading_level=3)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        # global + 2 H1 + 3 H2 + 1 H3 = 7
        assert len(chunks) == 7


QA_SAMPLE_MD = """# Sigma Spec

## LogSource

### category/product/service

**Q:** What is a logsource?
**A:** It describes the log data on which the detection is meant to be applied.

**Q:** Is logsource mandatory?
**A:** Yes. The logsource section is mandatory.

## Detection

### Condition

**Q:** What is the condition field for?
**A:** It specifies which search-identifier must evaluate to true.
"""


@pytest.fixture
def qa_file(tmp_path: Path) -> Path:
    f = tmp_path / "qa_spec.md"
    f.write_text(QA_SAMPLE_MD)
    return f


class TestMarkdownChunkerQA:
    def test_qa_chunks_produced(self, qa_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(qa_file)
        chunks = chunker.process(docs)
        qa_chunks = [c for c in chunks if c.metadata["chunk_type"] == "qa_pair"]
        assert len(qa_chunks) == 3

    def test_qa_no_chunks_when_no_qa(self, md_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(md_file)
        chunks = chunker.process(docs)
        qa_chunks = [c for c in chunks if c.metadata["chunk_type"] == "qa_pair"]
        assert len(qa_chunks) == 0

    def test_qa_h2_h3_context(self, qa_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(qa_file)
        chunks = chunker.process(docs)
        qa_chunks = [c for c in chunks if c.metadata["chunk_type"] == "qa_pair"]

        first = next(c for c in qa_chunks if "What is a logsource" in c.metadata["question"])
        assert first.metadata["h2_section"] == "LogSource"
        assert first.metadata["h3_section"] == "category/product/service"

        second = next(c for c in qa_chunks if "condition" in c.metadata["question"])
        assert second.metadata["h2_section"] == "Detection"
        assert second.metadata["h3_section"] == "Condition"

    def test_qa_both_chunk_types(self, qa_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(qa_file)
        chunks = chunker.process(docs)
        chunk_types = {c.metadata["chunk_type"] for c in chunks}
        assert "heading_h1" in chunk_types
        assert "heading_h2" in chunk_types
        assert "qa_pair" in chunk_types

    def test_qa_chunk_content(self, qa_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        docs = chunker.parse(qa_file)
        chunks = chunker.process(docs)
        qa = next(c for c in chunks if c.metadata["chunk_type"] == "qa_pair")

        assert qa.metadata["question"] == "What is a logsource?"
        assert "describes the log data" in qa.metadata["answer"]
        assert "logsource" in qa.text.lower()

    def test_qa_run_pipeline(self, qa_file: Path):
        config = TransformConfig(max_heading_level=2)
        chunker = MarkdownChunker(config)
        result = chunker.run(qa_file)
        qa_chunks = [c for c in result if c.metadata["chunk_type"] == "qa_pair"]
        assert len(qa_chunks) == 3
        assert all(c.metadata["collection"] == "default" for c in result)
