"""Sigma rule parser — emits empty-text Documents for downstream rich chunking."""

from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document

from ..base import DocumentTransform
from ..registry import TransformRegistry
from .loader import load_sigma_rules
from .detectors import is_sigma_rule

logger = logging.getLogger(__name__)


class SigmaParser(DocumentTransform):
    """Parse Sigma YAML files into LlamaIndex Document objects."""

    FORMAT_NAME = "sigma_rules"
    SUPPORTED_EXTENSIONS = (".yml", ".yaml")

    def parse(self, file_path: Path) -> list[Document]:
        """Load Sigma rules from a YAML file and return one Document per rule.

        Each Document has empty text and the full rule dict in
        ``metadata["rule_meta"]`` — rich chunking happens during chunk()
        via SigmaChunker, which needs ``rule_meta`` to expand each rule
        into its semantic chunks (executive_summary, logsource_context,
        detection_condition, ...).

        Setting ``rule_meta`` here is critical: without it, the chunker
        falls back to passing each rule through unchanged (one empty-text
        Document per rule) and the indexer ends up storing nothing.

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
                    "rule_id": rule_id,
                    "rule_meta": rule,
                },
            )
            documents.append(doc)
            logger.debug("Parsed rule '%s' (%s) from %s", title, rule_id, file_path)

        logger.info("Loaded %d rule(s) from %s", len(documents), file_path)
        return documents

    def chunk(self, documents: list[Document]) -> list[Document]:
        """Transform parsed documents into indexed chunks using SigmaChunker.

        Local import avoids circular dependency: chunker.py imports
        SigmaParser at module level.

        Args:
            documents: List of Document objects from parse().

        Returns:
            List of Document objects ready for embedding/indexing.
        """
        from .chunker import SigmaChunker  # noqa: PLC0415 — circular import

        chunker = SigmaChunker(config=self.config)
        return chunker.chunk(documents)


# Register the SigmaParser transform.
TransformRegistry.register(SigmaParser, formats=["sigma_rules"])
