"""Sigma rule parser — emits Documents with rule_meta for downstream processing."""

from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document

from ..base import DocumentTransform
from .loader import load_sigma_rules
from .detectors import is_sigma_rule

logger = logging.getLogger(__name__)


class SigmaParser(DocumentTransform):
    """Parse Sigma YAML files into LlamaIndex Document objects.

    This transform is **parse-only** — it sets ``rule_meta`` (the full rule
    dict) so that ``SigmaChunker.process()`` can later expand each rule into
    semantic chunks.  Use ``SigmaChunker`` for the full pipeline.
    """

    FORMAT_NAME = "sigma_rules"
    SUPPORTED_EXTENSIONS = (".yml", ".yaml")

    def parse(self, file_path: Path) -> list[Document]:
        """Load Sigma rules from a YAML file and return one Document per rule.

        Each Document has empty text.  Metadata includes the full rule dict
        under ``rule_meta`` (used by ``SigmaChunker.process()``).

        Args:
            file_path: Path to the YAML file containing one or more Sigma rules.

        Returns:
            List of Document objects, one per Sigma rule found.
        """
        raw_rules = load_sigma_rules(str(file_path))
        documents: list[Document] = []

        for rule in raw_rules:
            if not is_sigma_rule(rule):
                logger.debug("Skipping non-Sigma document in %s", file_path)
                continue

            rule_id = rule.get("id", "unknown")
            title = rule.get("title", "Untitled Sigma rule")

            doc = Document(
                text="",
                metadata={
                    "source_file": str(file_path),
                    "doc_type": "sigma_rule",
                    "file_name": file_path.name,
                    "rule_id": rule_id,
                    "rule_meta": rule,
                },
            )
            documents.append(doc)
            logger.debug("Parsed rule '%s' (%s) from %s", title, rule_id, file_path)

        logger.info("Loaded %d rule(s) from %s", len(documents), file_path)
        return documents

    def process(self, documents: list[Document]) -> list[Document]:
        raise NotImplementedError(
            "SigmaParser is parse-only. Use SigmaChunker for the full pipeline."
        )

    def output(self, documents: list[Document]) -> list[Document]:
        raise NotImplementedError(
            "SigmaParser is parse-only. Use SigmaChunker for the full pipeline."
        )

    def post_process(self, documents: list[Document]) -> list[Document]:
        raise NotImplementedError(
            "SigmaParser is parse-only. Use SigmaChunker for the full pipeline."
        )
