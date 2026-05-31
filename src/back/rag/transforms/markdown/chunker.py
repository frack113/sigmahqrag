"""Markdown document chunker for RAG pipeline.

Splits markdown files into hierarchical chunks based on heading levels.
Always produces a global chunk (full document), plus chunks per heading
down to the configured max_heading_level.

Usage:
    config = TransformConfig(max_heading_level=2)
    chunker = MarkdownChunker(config)
    documents = chunker.run(Path("doc.md"))
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from llama_index.core.schema import Document

from ..base import DocumentTransform
from ..registry import TransformRegistry

logger = logging.getLogger(__name__)

ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownChunker(DocumentTransform):
    """Chunk markdown files into heading-based Document objects.

    Chunk hierarchy (always includes global chunk):
    - ``max_heading_level=1`` → H1 chunks only
    - ``max_heading_level=2`` → H1 + H2 chunks (default)
    - ``max_heading_level=3`` → H1 + H2 + H3 chunks

    Each chunk includes content from its heading down to the next heading
    at the **same or higher** level, so parent chunks include all child
    content (e.g. an H1 chunk includes its H2/H3 sub-sections).
    """

    FORMAT_NAME = "markdown"
    SUPPORTED_EXTENSIONS = (".md", ".markdown")

    def parse(self, file_path: Path) -> list[Document]:
        raw = file_path.read_text(encoding="utf-8")
        return [
            Document(
                text=raw,
                metadata={
                    "source_file": str(file_path),
                    "doc_type": "markdown",
                    "file_name": file_path.name,
                },
            )
        ]

    def chunk(self, documents: list[Document]) -> list[Document]:
        result: list[Document] = []

        for doc in documents:
            text = doc.text or ""
            source = doc.metadata.get("source_file", "")

            result.append(
                Document(
                    text=text,
                    metadata={
                        **doc.metadata,
                        "chunk_type": "global",
                        "heading_level": 0,
                        "heading_text": "Document entier",
                    },
                )
            )

            headings = list(ATX_HEADING_RE.finditer(text))
            if not headings:
                continue

            for target_level in range(1, self.config.max_heading_level + 1):
                for i, match in enumerate(headings):
                    level = len(match.group(1))
                    if level != target_level:
                        continue

                    heading = match.group(2).strip()
                    start = match.end()

                    # find next heading at same or higher level
                    end = len(text)
                    for j in range(i + 1, len(headings)):
                        next_level = len(headings[j].group(1))
                        if next_level <= target_level:
                            end = headings[j].start()
                            break

                    content = text[start:end].strip()

                    # build breadcrumb path
                    path_parts: list[str] = []
                    for k in range(i, -1, -1):
                        lv = len(headings[k].group(1))
                        if lv < level:
                            path_parts.insert(0, headings[k].group(2).strip())
                        elif lv == level and k != i:
                            break
                    path_parts.append(heading)
                    heading_path = " > ".join(path_parts)

                    chunk_text = f"# {heading}\n\n{content}" if content else f"# {heading}"

                    result.append(
                        Document(
                            text=chunk_text.strip(),
                            metadata={
                                **doc.metadata,
                                "chunk_type": f"heading_h{level}",
                                "heading_level": level,
                                "heading_text": heading,
                                "heading_path": heading_path,
                                "source_file": source,
                            },
                        )
                    )

        logger.info(
            "Chunked %d doc(s) into %d markdown chunk(s)",
            len(documents),
            len(result),
        )
        return result

    def post_process(self, documents: list[Document]) -> list[Document]:
        return documents


TransformRegistry.register(MarkdownChunker)
