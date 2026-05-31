"""Rich chunking for Sigma rules — multiple semantic chunks per rule."""

from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document

from ..base import DocumentTransform
from ..registry import TransformRegistry
from .chunk_factory import make_chunk
from .flattening import flatten_detection_values, split_field_operator
from .formatting import format_value

logger = logging.getLogger(__name__)


class SigmaChunker(DocumentTransform):
    """Rich chunk Sigma rules into multiple semantic Document objects.

    Each Sigma rule is expanded into 12+ chunks:
    - executive_summary, rule_metadata_lifecycle, logsource_context,
      mitre_attack_mapping, detection_condition, detection_selection_block,
      detection_filter_block, field_operator_group, atomic_indicator,
      indicator_inventory, investigation_guidance, false_positive_context,
      natural_language_queries, backend_mapping_hints
    """

    FORMAT_NAME = "sigma_rules"
    SUPPORTED_EXTENSIONS = (".yml", ".yaml")

    def parse(self, file_path: Path) -> list[Document]:
        """Load Sigma rules from YAML (delegates to SigmaParser)."""
        from .loader import load_sigma_rules
        from .detectors import is_sigma_rule

        raw_rules = load_sigma_rules(str(file_path))
        documents: list[Document] = []

        for rule in raw_rules:
            if not is_sigma_rule(rule):
                continue

            rule_id = rule.get("id", "unknown")
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

        logger.info("Rich-parsed %d rule(s) from %s", len(documents), file_path)
        return documents

    def chunk(self, documents: list[Document]) -> list[Document]:
        """Produce multiple enriched chunks per Sigma rule document.

        Args:
            documents: List of Document objects with rule_meta in metadata.

        Returns:
            List of Document objects, one per rich chunk produced.
        """
        result: list[Document] = []
        for doc in documents:
            rule_meta = doc.metadata.get("rule_meta")
            if not rule_meta:
                # No rule data — pass through unchanged.
                result.append(doc)
                continue

            chunks = self._chunk_rule(rule_meta)
            for chunk_data in chunks:
                result.append(self._dict_to_document(chunk_data, doc.metadata.get("source_file")))

        logger.info("Expanded %d rules into %d rich chunks", len(documents), len(result))
        return result

    def post_process(self, documents: list[Document]) -> list[Document]:
        """Add eval questions as metadata for RAGAS evaluation."""
        if not self.config.enable_eval_questions:
            return documents

        for doc in documents:
            # Eval questions are already set in the chunk dict by make_chunk.
            pass
        return documents

    def _chunk_rule(self, rule: dict) -> list[dict]:
        """Chunk a single Sigma rule dict into enriched chunk dicts.

        This is the refactored version of the legacy chunk_sigma_rules_rich function.
        """
        title = rule.get("title", "Untitled Sigma rule")
        rule_id = rule.get("id")
        description = rule.get("description", "")
        level = rule.get("level", "unknown")
        status = rule.get("status", "unknown")
        tags = rule.get("tags", [])
        logsource = rule.get("logsource", {})
        detection = rule.get("detection", {})
        condition = detection.get("condition", "")
        falsepositives = rule.get("falsepositives", [])
        references = rule.get("references", [])
        author = rule.get("author", "")
        date = rule.get("date", "")
        modified = rule.get("modified", "")

        product = logsource.get("product", "unknown")
        category = logsource.get("category", "unknown")
        service = logsource.get("service", "unknown")

        chunks: list[dict] = []

        # Executive summary
        chunks.append(
            make_chunk(
                rule,
                "executive_summary",
                (
                    f"Sigma rule: {title}\n"
                    f"Rule ID: {rule_id}\n"
                    f"Purpose: {description}\n"
                    f"This rule is designed for {product} logs with "
                    f"category={category} and service={service}.\n"
                    f"Severity: {level}. Status: {status}.\n"
                    f"Main detection logic: {condition}"
                ),
                eval_questions=self._summarize_questions(title),
            )
        )

        # Rule metadata and lifecycle
        chunks.append(
            make_chunk(
                rule,
                "rule_metadata_lifecycle",
                (
                    f"Rule metadata for {title}.\n"
                    f"Rule ID: {rule_id}\n"
                    f"Author: {author}\n"
                    f"Created date: {date}\n"
                    f"Modified date: {modified}\n"
                    f"Status: {status}\n"
                    f"Level: {level}"
                ),
                extra_meta={"references": references},
                eval_questions=self._lifecycle_questions(title),
            )
        )

        # Logsource context
        chunks.append(
            make_chunk(
                rule,
                "logsource_context",
                (
                    f"Logsource context for Sigma rule {title}.\n"
                    f"Product: {product}\n"
                    f"Category: {category}\n"
                    f"Service: {service}\n"
                    f"The rule expects telemetry from product={product}, "
                    f"category={category}, service={service}."
                ),
                eval_questions=self._logsource_questions(title, product, category, service),
            )
        )

        # MITRE ATT&CK mapping
        attack_tags = [tag for tag in tags if str(tag).startswith("attack.")]
        if attack_tags:
            chunks.append(
                make_chunk(
                    rule,
                    "mitre_attack_mapping",
                    (f"MITRE ATT&CK mapping for {title}.\nTags:\n{format_value(attack_tags)}"),
                    extra_meta={"attack_tags": attack_tags},
                    eval_questions=self._attck_questions(title, attack_tags),
                )
            )

        # Detection condition
        chunks.append(
            make_chunk(
                rule,
                "detection_condition",
                (
                    f"Detection condition for {title}.\n"
                    f"Condition: {condition}\n"
                    f"Interpretation: this condition defines how selection and "
                    f"filter blocks are combined to trigger the rule."
                ),
                extra_meta={"condition": condition},
                eval_questions=[
                    f"What is the Sigma condition of {title}?",
                    f"How are selections and filters combined in {title}?",
                    f"Que signifie la condition de détection de {title} ?",
                ],
            )
        )

        # Iteration over detection blocks
        all_atomic_facts: list[dict] = []
        for detection_name, detection_value in detection.items():
            if detection_name == "condition":
                continue

            is_filter = detection_name.startswith("filter")
            chunk_type = "detection_filter_block" if is_filter else "detection_selection_block"

            facts = flatten_detection_values(detection_value)
            all_atomic_facts.extend(
                [
                    {
                        "detection_name": detection_name,
                        **fact,
                        "is_filter": is_filter,
                    }
                    for fact in facts
                ]
            )

            # Detection block chunk
            chunks.append(
                make_chunk(
                    rule,
                    chunk_type,
                    (
                        f"Detection block {detection_name} in Sigma rule {title}.\n"
                        f"Block role: {'exclusion / false positive reduction' if is_filter else 'positive detection indicator'}\n"
                        f"Raw block:\n{format_value(detection_value)}"
                    ),
                    extra_meta={
                        "detection_name": detection_name,
                        "is_filter": is_filter,
                    },
                    eval_questions=self._block_questions(title, detection_name, is_filter),
                )
            )

            # Field/operator groups
            by_field_operator: dict[str, list] = {}
            for fact in facts:
                by_field_operator.setdefault(fact["field_operator"], []).append(fact["value"])

            for field_operator, values in by_field_operator.items():
                field, operator = split_field_operator(field_operator)
                chunks.append(
                    make_chunk(
                        rule,
                        "field_operator_group",
                        (
                            f"Field/operator group in {title}.\n"
                            f"Detection block: {detection_name}\n"
                            f"Field: {field}\n"
                            f"Operator: {operator}\n"
                            f"Role: {'filter/exclusion' if is_filter else 'indicator/selection'}\n"
                            f"Values:\n{format_value(values)}"
                        ),
                        extra_meta={
                            "detection_name": detection_name,
                            "field": field,
                            "operator": operator,
                            "is_filter": is_filter,
                        },
                        eval_questions=self._field_questions(title, field, operator),
                    )
                )

            # Atomic indicators
            for fact in facts:
                field, operator = split_field_operator(fact["field_operator"])
                value = fact["value"]
                chunks.append(
                    make_chunk(
                        rule,
                        "atomic_indicator",
                        (
                            f"Atomic Sigma indicator for {title}.\n"
                            f"Detection block: {detection_name}\n"
                            f"Field: {field}\n"
                            f"Operator: {operator}\n"
                            f"Value: {value}\n"
                            f"Role: {'legitimate exclusion / filter' if is_filter else 'suspicious or monitored indicator'}\n"
                            f"A match on this value contributes to the rule condition: {condition}"
                        ),
                        extra_meta={
                            "detection_name": detection_name,
                            "field": field,
                            "operator": operator,
                            "value": value,
                            "is_filter": is_filter,
                        },
                        eval_questions=self._indicator_questions(title, value),
                    )
                )

        # Indicator inventory
        suspicious_values = [f for f in all_atomic_facts if not f["is_filter"]]
        filter_values = [f for f in all_atomic_facts if f["is_filter"]]
        chunks.append(
            make_chunk(
                rule,
                "indicator_inventory",
                (
                    f"Indicator inventory for {title}.\n"
                    f"Suspicious or monitored values:\n"
                    f"{format_value([f['value'] for f in suspicious_values])}\n\n"
                    f"Filtered legitimate values:\n"
                    f"{format_value([f['value'] for f in filter_values])}"
                ),
                eval_questions=[
                    f"List all monitored values in {title}.",
                    f"What indicators are monitored by {title}?",
                    f"Which values are excluded by {title}?",
                ],
            )
        )

        # Investigation guidance
        chunks.append(
            make_chunk(
                rule,
                "investigation_guidance",
                (
                    f"Investigation guidance for alerts from {title}.\n"
                    f"Investigate the entity, user, process, host, timestamp, "
                    f"and event context that matched the Sigma rule.\n"
                    f"Review whether the matched values are expected in the environment."
                ),
                eval_questions=[
                    f"How should an analyst investigate alerts from {title}?",
                    f"What context matters for {title} alerts?",
                    f"Que faut-il vérifier lors d'une alerte {title} ?",
                ],
            )
        )

        # False positive context
        chunks.append(
            make_chunk(
                rule,
                "false_positive_context",
                (
                    f"False positive context for {title}.\n"
                    f"False positives:\n{format_value(falsepositives)}\n"
                    f"Common benign causes may include administrative activity, "
                    f"automation, package managers, security tools."
                ),
                eval_questions=[
                    f"What false positives can occur for {title}?",
                    f"How can false positives be reduced for {title}?",
                    f"Quels faux positifs sont attendus pour {title} ?",
                ],
            )
        )

        # Natural language queries
        chunks.append(
            make_chunk(
                rule,
                "natural_language_queries",
                (
                    f"Natural language retrieval hints for {title}.\n"
                    f"This rule is relevant for questions such as:\n"
                    f"- What does {title} detect?\n"
                    f"- Which detection fields and values are used?\n"
                    f"- What logsource is required?"
                ),
                eval_questions=[
                    f"Which rule detects behavior described by {title}?",
                    f"What fields are used by {title}?",
                    f"What ATT&CK mapping is associated with {title}?",
                ],
            )
        )

        # Backend mapping hints
        chunks.append(
            make_chunk(
                rule,
                "backend_mapping_hints",
                (
                    f"Backend mapping hints for {title}.\n"
                    f"The detection fields should be mapped to the corresponding "
                    f"SIEM, EDR, or log backend schema.\n"
                    f"Operators from Sigma such as contains, startswith, endswith, "
                    f"all, and equals should be preserved during translation.\n"
                    f"Condition: {condition}"
                ),
                eval_questions=[
                    f"What fields should be mapped for {title}?",
                    f"How should {title} be translated to a SIEM query?",
                    f"What operators are used in {title}?",
                ],
            )
        )

        return chunks

    def _dict_to_document(self, chunk_data: dict, source_file: str | None = None) -> Document:
        """Convert a chunk dict to a LlamaIndex Document."""
        metadata = chunk_data.get("metadata", {}).copy()
        if source_file:
            metadata["source_file"] = source_file

        return Document(
            text=chunk_data.get("text", ""),
            metadata=metadata,
            excluded_embed_metadata_keys=[]
            if not self.config.enable_rich_chunks
            else ["chunk_type", "source_file"],
        )

    # ------------------------------------------------------------------
    # Eval question generators
    # ------------------------------------------------------------------

    def _summarize_questions(self, title: str) -> list[str]:
        return [
            f"What does the Sigma rule {title} detect?",
            f"Explain the purpose of {title}.",
            f"Quelle est l'intention de la règle Sigma {title} ?",
        ]

    def _lifecycle_questions(self, title: str) -> list[str]:
        return [
            f"Who authored {title}?",
            f"When was {title} modified?",
            f"What is the lifecycle status of {title}?",
        ]

    def _logsource_questions(
        self, title: str, product: str, category: str, service: str
    ) -> list[str]:
        return [
            f"What logsource is required for {title}?",
            f"Which telemetry category does {title} use?",
            f"Sur quel produit la règle {title} s'applique-t-elle ?",
        ]

    def _attck_questions(self, title: str, attack_tags: list[str]) -> list[str]:
        return [
            f"What MITRE ATT&CK techniques are mapped to {title}?",
            f"Which ATT&CK tactic is relevant to {title}?",
            f"What Sigma rule maps to {', '.join(map(str, attack_tags))}?",
        ]

    def _block_questions(self, title: str, detection_name: str, is_filter: bool) -> list[str]:
        return [
            f"What does detection block {detection_name} contain?",
            f"Which values are checked in {detection_name}?",
            f"Is {detection_name} a detection or a filter?",
        ]

    def _field_questions(self, title: str, field: str, operator: str) -> list[str]:
        return [
            f"What values does {title} check for field {field}?",
            f"What operator is used on {field} in {title}?",
            f"Which rule contains {field}|{operator}?",
        ]

    def _indicator_questions(self, title: str, value: str) -> list[str]:
        return [
            f"Which Sigma rule detects {value}?",
            f"Is {value} suspicious or filtered?",
            f"What field contains {value} in {title}?",
        ]

    def _generate_eval_questions(self, rule: dict) -> dict[str, list[str]]:
        """Generate eval question groups for a rule (for flat-mode post_process)."""
        title = rule.get("title", "Untitled Sigma rule")
        return {
            "summary": self._summarize_questions(title),
            "lifecycle": self._lifecycle_questions(title),
            "logsource": self._logsource_questions(
                title,
                rule.get("logsource", {}).get("product", "unknown"),
                rule.get("logsource", {}).get("category", "unknown"),
                rule.get("logsource", {}).get("service", "unknown"),
            ),
        }


# Register SigmaChunker for rich mode.
TransformRegistry.register(SigmaChunker, formats=["sigma_rules"])


# ------------------------------------------------------------------
# Backwards-compatible function
# ------------------------------------------------------------------


def chunk_sigma_rules_rich(rule: dict) -> list[dict]:
    """Legacy entry-point: chunk a single Sigma rule dict into enriched chunks.

    Kept for backwards compatibility. New code should use SigmaChunker.chunk()
    via the DocumentTransform contract.
    """
    chunker = SigmaChunker()
    return chunker._chunk_rule(rule)
