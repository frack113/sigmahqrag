"""Markdown document chunker for RAG pipeline.

Splits markdown files into hierarchical chunks based on heading levels.
Uses LLM to generate dynamic keywords per chunk for better semantic recall.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from llama_index.core.schema import Document

from ...base import DocumentTransform
from ...registry import TransformRegistry
from ..llm import LLMClientLike, enrich_by_llm

logger = logging.getLogger(__name__)

ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _extract_keywords(text: str, llm_client: LLMClientLike | None) -> tuple[str, str]:
    """Extract summary and keywords from text via LLM.

    Args:
        text: The chunk text to enrich.
        llm_client: LLM client instance or None (skips enrichment).

    Returns:
        Tuple of (summary, keywords) strings.
    """
    if not llm_client:
        return "", ""
    result = enrich_by_llm(text, llm_client)
    return (result.get("summary") or ""), (result.get("keywords") or "")


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

    def process(self, documents: list[Document]) -> list[Document]:
        """Chunk markdown into heading-based chunks with inline LLM enrichment.

        Chunking and enrichment are performed in a single pass since each
        heading chunk is enriched independently as it is created.
        """
        result: list[Document] = []

        for doc in documents:
            text = doc.text or ""
            source = doc.metadata.get("source_file", "")

            llm_client = getattr(self.config, "llm_client", None)

            # Global chunk (full document)
            global_text = text
            global_summary = ""
            global_keywords = ""
            if llm_client:
                try:
                    global_summary, global_keywords = _extract_keywords(global_text, llm_client)
                except Exception as e:
                    logger.warning("LLM enrichment for global chunk failed: %s", e)

            enriched_global = global_text
            if global_summary or global_keywords:
                enriched_global = self._inject_enrichment(
                    global_text, global_summary, global_keywords
                )

            result.append(
                Document(
                    text=enriched_global,
                    metadata={
                        **doc.metadata,
                        "chunk_type": "global",
                        "heading_level": 0,
                        "heading_text": "Document entier",
                        "has_llm_enrichment": bool(global_summary or global_keywords),
                    },
                )
            )

            # Try to erase KV cache after LLM enrichment (non-destructive)
            if llm_client and hasattr(llm_client, "erase_slot_cache"):
                try:
                    llm_client.erase_slot_cache()
                    logger.debug("KV cache erased after markdown enrichment")
                except Exception:
                    logger.debug("KV cache erase failed, llama.cpp may not support slot management")

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

                    # LLM summary + keyword extraction for this chunk
                    chunk_summary = ""
                    chunk_keywords = ""
                    if llm_client:
                        try:
                            chunk_summary, chunk_keywords = _extract_keywords(
                                chunk_text, llm_client
                            )
                        except Exception as e:
                            logger.warning("LLM enrichment for heading %s failed: %s", heading, e)

                    if llm_client and hasattr(llm_client, "erase_slot_cache"):
                        try:
                            llm_client.erase_slot_cache()
                        except Exception:
                            logger.debug("KV cache erase failed for heading %s", heading)

                    enriched = chunk_text
                    if chunk_summary or chunk_keywords:
                        enriched = self._inject_enrichment(
                            chunk_text, chunk_summary, chunk_keywords
                        )

                    result.append(
                        Document(
                            text=enriched.strip(),
                            metadata={
                                **doc.metadata,
                                "chunk_type": f"heading_h{level}",
                                "heading_level": level,
                                "heading_text": heading,
                                "heading_path": heading_path,
                                "source_file": source,
                                "has_llm_enrichment": bool(chunk_summary or chunk_keywords),
                            },
                        )
                    )

        # Always keep at least the global chunk; filter other truly empty chunks
        filtered = [
            doc
            for doc in result
            if (doc.text or "").strip() or doc.metadata.get("chunk_type") == "global"
        ]
        kept = len(result) - len(filtered)
        if kept:
            logger.debug("Filtered %d empty chunks from %d total", kept, len(result))

        source = documents[0].metadata.get("file_name", "?") if documents else "?"
        logger.info(
            "Chunked %s into %d markdown chunk(s)",
            source,
            len(filtered),
        )
        return filtered

    def post_process(self, documents: list[Document]) -> list[Document]:
        return documents

    @staticmethod
    def _inject_enrichment(text: str, summary: str, keywords: str) -> str:
        """Append LLM-generated summary and keywords at the end of the text for embedding."""
        enrichment = "\n\n---\n"
        if summary:
            enrichment += f"Summary: {summary}\n\n"
        if keywords:
            enrichment += f"Keywords: {keywords}\n"
        return text + enrichment


TransformRegistry.register(MarkdownChunker)
