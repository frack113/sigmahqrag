"""Markdown document chunker for RAG pipeline.

Splits markdown files into hierarchical chunks based on heading levels.
Uses LLM to generate dynamic keywords per chunk for better semantic recall.
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

import httpx
from llama_index.core.schema import Document

from ..base import DocumentTransform
from ..registry import TransformRegistry

logger = logging.getLogger(__name__)

ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# LLM prompt for summary + keyword extraction
_LLM_ENRICH_PROMPT = """Given the following document section, provide:
1. A concise summary in 2-3 sentences (max 150 words)
2. A comma-separated list of 8-15 key search keywords/phrases

Rules:
- Summary should capture the main topic and key points
- Keywords should include both technical terms and natural-language synonyms
- Focus on domain-specific concepts, not generic words
- Use English even if the source text is in another language
- Output format (EXACTLY):

Summary:
[your 2-3 sentence summary here]

Keywords:
[comma-separated keywords here]

Document section:
---
{text}
---

Summary:"""


class _StaticLlamaClient:
    """Minimal sync wrapper around httpx for LLM enrichment (summary + keywords)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{self.base_url}/v1/completions",
                    json={
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                choices = resp.json().get("choices") or []
                return (choices[0].get("text") or "").strip() if choices else ""
        except Exception as e:
            logger.debug("LLM enrichment failed: %s", e)
            return ""


# Global LLM client singleton (lazy-initialized)
_llm_client: _StaticLlamaClient | None = None
_llm_lock = threading.Lock()


def _get_llm_client() -> _StaticLlamaClient:
    global _llm_client
    if _llm_client is None:
        with _llm_lock:
            if _llm_client is None:
                _llm_client = _StaticLlamaClient()
    return _llm_client


def _extract_keywords(text: str, llm_client: _StaticLlamaClient | None = None) -> tuple[str, str]:
    """Extract summary and keywords from text via LLM.

    Args:
        text: The chunk text to enrich.
        llm_client: Optional LLM client (uses default if not provided).

    Returns:
        Tuple of (summary, keywords) strings.
    """
    client = llm_client or _get_llm_client()
    prompt = _LLM_ENRICH_PROMPT.format(text=text[:2000])
    result = client.generate(prompt, max_tokens=512, temperature=0.3)

    summary = ""
    keywords = ""
    if result:
        # Parse Summary: and Keywords: sections
        parts = result.split("\n\n")
        for part in parts:
            part = part.strip()
            if part.startswith("Summary:") or part.startswith("Summary :"):
                summary = part.replace("Summary:", "").replace("Summary :", "").strip()
            elif part.startswith("Keywords:") or part.startswith("Keywords :"):
                keywords = part.replace("Keywords:", "").replace("Keywords :", "").strip()

    return summary, keywords


class MarkdownChunker(DocumentTransform):
    """Chunk markdown files into heading-based Document objects.

    Uses LLM-based keyword extraction for each chunk when an LLM client is
    configured via ``TransformConfig.llm_client`` or when running in an
    environment where keyword generation is enabled.

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

            # Determine LLM client
            llm_client = None
            enable_llm = False
            client = self.config.llm_client if hasattr(self.config, "llm_client") else None
            if client is not None:
                llm_client = client
                enable_llm = True
            elif hasattr(self.config, "enable_llm_enrichment"):
                enable_llm = self.config.enable_llm_enrichment and True
            else:
                enable_llm = True

            if enable_llm and llm_client is None:
                llm_client = _get_llm_client()

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

    @staticmethod
    def _enrich_text(text: str) -> str:
        """Fallback enrichment (no longer used when LLM is available)."""
        return text


TransformRegistry.register(MarkdownChunker)
