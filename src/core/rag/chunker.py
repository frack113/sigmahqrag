"""Sigma rule chunker for RAG pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from llama_index.core.schema import Document

from src.core.schemas.sigma_rule import SigmaRule

logger = logging.getLogger(__name__)

MAX_TOKENS = 512


def count_tokens(text: str) -> int:
    """Estimate token count using word count approximation."""
    return len(text.split())


def load_sigma_rule(file_path: Path) -> list[SigmaRule]:
    """Load Sigma rules from a YAML file."""
    rules: list[SigmaRule] = []
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            line_number = 1
            for line in content.split("\n"):
                if line.strip().startswith("title:"):
                    rule_data = yaml.safe_load(content)
                    if isinstance(rule_data, dict):
                        rule = SigmaRule.from_dict(rule_data, file_path, line_number)
                        rules.append(rule)
                    break
    except Exception as e:
        logger.error(f"Failed to load Sigma rule from {file_path}: {e}")
    return rules


def load_sigma_rules_from_directory(
    directory: Path, pattern: str = "*.yaml"
) -> list[SigmaRule]:
    """Load all Sigma rules from a directory."""
    rules: list[SigmaRule] = []
    for file_path in directory.glob(pattern):
        rules.extend(load_sigma_rule(file_path))
    return rules


def chunk_sigma_rule(rule: SigmaRule) -> list[Document]:
    """Chunk a Sigma rule into LlamaIndex Documents."""
    chunks: list[Document] = []
    file_path = str(rule.file_path) if rule.file_path else ""
    line_start = rule.line_number or 1
    metadata: dict[str, Any] = {
        "file_path": file_path,
        "line_start": line_start,
        "rule_id": rule.id,
        "title": rule.title,
    }

    chunk_content: list[str] = []
    current_tokens = 0

    def emit_chunk(text: str, chunk_metadata: dict[str, Any]) -> None:
        """Emit a chunk if it has content."""
        if text.strip():
            chunks.append(Document(text=text.strip(), metadata=chunk_metadata))

    if rule.title:
        title_text = f"Title: {rule.title}"
        chunk_content.append(title_text)
        current_tokens += count_tokens(title_text)

    if rule.description:
        desc_text = f"Description: {rule.description}"
        if current_tokens + count_tokens(desc_text) > MAX_TOKENS:
            emit_chunk("\n".join(chunk_content), metadata.copy())
            chunk_content = [desc_text]
            current_tokens = count_tokens(desc_text)
        else:
            chunk_content.append(desc_text)
            current_tokens += count_tokens(desc_text)

    detection_str = _format_detection(rule.detection)
    if detection_str:
        if current_tokens + count_tokens(detection_str) > MAX_TOKENS:
            emit_chunk("\n".join(chunk_content), metadata.copy())
            chunk_content = [detection_str]
            current_tokens = count_tokens(detection_str)
        else:
            chunk_content.append(detection_str)
            current_tokens += count_tokens(detection_str)

    if rule.fields:
        fields_text = f"Fields: {', '.join(rule.fields)}"
        if current_tokens + count_tokens(fields_text) > MAX_TOKENS:
            emit_chunk("\n".join(chunk_content), metadata.copy())
            chunk_content = [fields_text]
            current_tokens = count_tokens(fields_text)
        else:
            chunk_content.append(fields_text)
            current_tokens += count_tokens(fields_text)

    if rule.falsepositives:
        fp_text = f"Falsepositives: {', '.join(rule.falsepositives)}"
        if current_tokens + count_tokens(fp_text) > MAX_TOKENS:
            emit_chunk("\n".join(chunk_content), metadata.copy())
            chunk_content = [fp_text]
        else:
            chunk_content.append(fp_text)

    status_text = f"Status: {rule.status}, Level: {rule.level}"
    if chunk_content:
        chunk_content.append(status_text)

    emit_chunk("\n".join(chunk_content), metadata.copy())

    if not chunks:
        chunks.append(
            Document(text=f"{rule.title}: {detection_str}", metadata=metadata)
        )

    return chunks


def _format_detection(detection: dict[str, Any]) -> str:
    """Format detection section as text."""
    if not detection:
        return ""

    parts: list[str] = []
    if "condition" in detection:
        parts.append(f"Condition: {detection['condition']}")

    for key, value in detection.items():
        if key == "condition":
            continue
        if isinstance(value, dict):
            parts.append(f"{key}: {value.get('selection', value)}")
        else:
            parts.append(f"{key}: {value}")

    return "\n".join(parts)


class SigmaChunker:
    """Sigma rule chunker for RAG pipeline."""

    def __init__(self, max_tokens: int = MAX_TOKENS) -> None:
        """Initialize chunker."""
        self.max_tokens = max_tokens

    def chunk_file(self, file_path: Path) -> list[Document]:
        """Chunk a Sigma rule file."""
        rules = load_sigma_rule(file_path)
        chunks: list[Document] = []
        for rule in rules:
            rule_chunks = chunk_sigma_rule(rule)
            chunks.extend(rule_chunks)
        return chunks

    def chunk_directory(
        self, directory: Path, pattern: str = "*.yaml"
    ) -> list[Document]:
        """Chunk all Sigma rules in a directory."""
        rules = load_sigma_rules_from_directory(directory, pattern)
        chunks: list[Document] = []
        for rule in rules:
            rule_chunks = chunk_sigma_rule(rule)
            chunks.extend(rule_chunks)
        return chunks
