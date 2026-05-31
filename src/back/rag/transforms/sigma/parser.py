"""Sigma rule parser using the legacy loader + detector."""

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

        In flat mode, each rule is wrapped in a Document with its text representation.
        In rich mode, text is empty and chunking happens during chunk().

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

            if self.config.enable_rich_chunks:
                text = ""
            else:
                text = _rule_dict_to_text(rule)

            doc = Document(
                text=text,
                metadata={
                    "source_file": str(file_path),
                    "doc_type": "sigma_rule",
                    "rule_id": rule_id,
                },
            )
            documents.append(doc)
            logger.debug("Parsed rule '%s' (%s) from %s", title, rule_id, file_path)

        logger.info("Loaded %d rule(s) from %s", len(documents), file_path)
        return documents

    def chunk(self, documents: list[Document]) -> list[Document]:
        """Transform parsed documents into indexed chunks.

        In flat mode, returns documents unchanged (one doc = one chunk).
        In rich mode, delegates to SigmaChunker to produce multiple chunks per rule.

        Args:
            documents: List of Document objects from parse().

        Returns:
            List of Document objects ready for embedding/indexing.
        """
        if self.config.enable_rich_chunks:
            from .chunker import SigmaChunker

            chunker = SigmaChunker(config=self.config)
            return chunker.chunk(documents)
        return documents


# ------------------------------------------------------------------
# Flat-mode text builder (mirrors indexing._sigma_rule_to_text)
# ------------------------------------------------------------------


def _rule_dict_to_text(rule: dict) -> str:
    """Convert a Sigma rule dict to a flat text representation.

    This is the legacy behavior: one rule = one text block for embedding.

    Args:
        rule: Sigma rule dict with keys like title, description, detection, etc.

    Returns:
        A flat text string suitable for embedding.
    """
    parts = [f"Title: {rule.get('title', 'Untitled Sigma rule')}"]

    description = rule.get("description")
    if description:
        parts.append(f"Description: {description}")

    logsource = rule.get("logsource", {})
    if logsource:
        product = logsource.get("product", "unknown")
        category = logsource.get("category", "unknown")
        service = logsource.get("service", "unknown")
        parts.append(f"Logsource: product={product}, category={category}, service={service}")

    condition = rule.get("detection", {}).get("condition", "")
    if condition:
        parts.append(f"Condition: {condition}")

    tags = rule.get("tags", [])
    if tags:
        parts.append(f"Tags: {', '.join(str(t) for t in tags)}")

    level = rule.get("level")
    if level:
        parts.append(f"Level: {level}")

    return "\n".join(parts)


# Register the SigmaParser transform.
TransformRegistry.register(SigmaParser, formats=["sigma_rules"])
