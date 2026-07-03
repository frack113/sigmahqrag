"""Rich chunking for Sigma rules — multiple semantic chunks per rule."""

from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document

from ..base import DocumentTransform
from ..document.llm import LLMClientLike, enrich_by_llm
from ..registry import TransformRegistry
from .chunk_factory import make_chunk
from .flattening import flatten_detection_values, split_field_operator
from .formatting import format_value
from .parser import SigmaParser

logger = logging.getLogger(__name__)


class SigmaChunker(DocumentTransform):
    """Rich chunk Sigma rules into multiple semantic Document objects.

    Each Sigma rule is expanded into 12+ chunks:
    - executive_summary, rule_metadata_lifecycle, logsource_context,
      mitre_attack_mapping, detection_condition, detection_selection_block,
      detection_filter_block, field_operator_group, atomic_indicator,
      indicator_inventory, investigation_guidance, false_positive_context,
      natural_language_queries, backend_mapping_hints

    ``parse()`` delegates to ``SigmaParser`` which sets ``rule_meta``.
    ``process()`` reads ``rule_meta`` and produces all 12+ chunk types
    with LLM enrichment inline.
    """

    FORMAT_NAME = "sigma"
    SUPPORTED_EXTENSIONS = (".yml", ".yaml")

    def parse(self, file_path: Path) -> list[Document]:
        """Delegate to ``SigmaParser`` to load rules with ``rule_meta``."""
        parser = SigmaParser(config=self.config)
        return parser.parse(file_path)

    def process(self, documents: list[Document]) -> list[Document]:
        """Produce multiple enriched chunks per Sigma rule document.

        Reads ``rule_meta`` from each document's metadata and expands it
        into 12+ semantic chunks with inline LLM enrichment.

        Args:
            documents: List of Document objects with rule_meta in metadata.

        Returns:
            List of Document objects, one per rich chunk produced.
        """
        llm_client = getattr(self.config, "llm_client", None)

        result: list[Document] = []
        for doc in documents:
            rule_meta = doc.metadata.get("rule_meta")
            if not rule_meta:
                raise ValueError(
                    "SigmaChunker.process() requires rule_meta in metadata. "
                    "Use SigmaParser.parse() or SigmaChunker.parse() first."
                )

            chunks = self._chunk_rule(rule_meta, llm_client=llm_client)
            for chunk_data in chunks:
                result.append(self._dict_to_document(chunk_data, doc.metadata.get("source_file")))

        logger.info("Expanded %d rules into %d rich chunks", len(documents), len(result))

        if llm_client is not None:
            try:
                llm_client.erase_slot_cache()
                logger.info("KV cache erased after Sigma rule enrichment")
            except Exception:
                logger.debug("KV cache erase failed, llama.cpp may not support slot management")

        return result

    def post_process(self, documents: list[Document]) -> list[Document]:
        """Add eval questions as metadata for RAGAS evaluation."""
        if not self.config.enable_eval_questions:
            return documents

        return documents

    def _extract_fields(self, rule: dict) -> dict:
        return {
            "title": rule.get("title", "Untitled Sigma rule"),
            "rule_id": rule.get("id"),
            "description": rule.get("description", ""),
            "level": rule.get("level", "unknown"),
            "status": rule.get("status", "unknown"),
            "tags": rule.get("tags", []),
            "detection": rule.get("detection", {}),
            "condition": rule.get("detection", {}).get("condition", ""),
            "falsepositives": rule.get("falsepositives", []),
            "references": rule.get("references", []),
            "author": rule.get("author", ""),
            "date": rule.get("date", ""),
            "modified": rule.get("modified", ""),
            "product": rule.get("logsource", {}).get("product", "unknown"),
            "category": rule.get("logsource", {}).get("category", "unknown"),
            "service": rule.get("logsource", {}).get("service", "unknown"),
        }

    def _build_executive_summary(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "executive_summary",
            (
                f"Sigma rule: {f['title']}\n"
                f"Rule ID: {f['rule_id']}\n"
                f"Purpose: {f['description']}\n"
                f"This rule is designed for {f['product']} logs with "
                f"category={f['category']} and service={f['service']}.\n"
                f"Severity: {f['level']}. Status: {f['status']}.\n"
                f"Main detection logic: {f['condition']}"
            ),
            eval_questions=self._summarize_questions(f["title"]),
        )

    def _build_metadata_lifecycle(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "rule_metadata_lifecycle",
            (
                f"Rule metadata for {f['title']}.\n"
                f"Rule ID: {f['rule_id']}\n"
                f"Author: {f['author']}\n"
                f"Created date: {f['date']}\n"
                f"Modified date: {f['modified']}\n"
                f"Status: {f['status']}\n"
                f"Level: {f['level']}"
            ),
            extra_meta={"references": f["references"]},
            eval_questions=self._lifecycle_questions(f["title"]),
        )

    def _build_logsource_context(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "logsource_context",
            (
                f"Logsource context for Sigma rule {f['title']}.\n"
                f"Product: {f['product']}\n"
                f"Category: {f['category']}\n"
                f"Service: {f['service']}\n"
                f"The rule expects telemetry from product={f['product']}, "
                f"category={f['category']}, service={f['service']}."
            ),
            eval_questions=self._logsource_questions(
                f["title"], f["product"], f["category"], f["service"]
            ),
        )

    def _build_mitre_attack_mapping(self, rule: dict, f: dict) -> dict | None:
        attack_tags = [tag for tag in f["tags"] if str(tag).startswith("attack.")]
        if not attack_tags:
            return None
        return make_chunk(
            rule,
            "mitre_attack_mapping",
            f"MITRE ATT&CK mapping for {f['title']}.\nTags:\n{format_value(attack_tags)}",
            extra_meta={"attack_tags": attack_tags},
            eval_questions=self._attck_questions(f["title"], attack_tags),
        )

    def _build_detection_condition(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "detection_condition",
            (
                f"Detection condition for {f['title']}.\n"
                f"Condition: {f['condition']}\n"
                f"Interpretation: this condition defines how selection and "
                f"filter blocks are combined to trigger the rule."
            ),
            extra_meta={"condition": f["condition"]},
            eval_questions=[
                f"What is the Sigma condition of {f['title']}?",
                f"How are selections and filters combined in {f['title']}?",
                f"Que signifie la condition de détection de {f['title']} ?",
            ],
        )

    def _build_detection_block_chunks(self, rule: dict, f: dict) -> tuple[list[dict], list[dict]]:
        chunks: list[dict] = []
        all_atomic_facts: list[dict] = []
        for detection_name, detection_value in f["detection"].items():
            if detection_name == "condition":
                continue
            is_filter = detection_name.startswith("filter")
            chunk_type = "detection_filter_block" if is_filter else "detection_selection_block"
            facts = flatten_detection_values(detection_value)
            all_atomic_facts.extend(
                {"detection_name": detection_name, **fact, "is_filter": is_filter} for fact in facts
            )
            chunks.append(
                make_chunk(
                    rule,
                    chunk_type,
                    (
                        f"Detection block {detection_name} in Sigma rule {f['title']}.\n"
                        f"Block role: {'exclusion / false positive reduction' if is_filter else 'positive detection indicator'}\n"
                        f"Raw block:\n{format_value(detection_value)}"
                    ),
                    extra_meta={"detection_name": detection_name, "is_filter": is_filter},
                    eval_questions=self._block_questions(f["title"], detection_name, is_filter),
                )
            )
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
                            f"Field/operator group in {f['title']}.\n"
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
                        eval_questions=self._field_questions(f["title"], field, operator),
                    )
                )
            for fact in facts:
                field, operator = split_field_operator(fact["field_operator"])
                value = fact["value"]
                chunks.append(
                    make_chunk(
                        rule,
                        "atomic_indicator",
                        (
                            f"Atomic Sigma indicator for {f['title']}.\n"
                            f"Detection block: {detection_name}\n"
                            f"Field: {field}\n"
                            f"Operator: {operator}\n"
                            f"Value: {value}\n"
                            f"Role: {'legitimate exclusion / filter' if is_filter else 'suspicious or monitored indicator'}\n"
                            f"A match on this value contributes to the rule condition: {f['condition']}"
                        ),
                        extra_meta={
                            "detection_name": detection_name,
                            "field": field,
                            "operator": operator,
                            "value": value,
                            "is_filter": is_filter,
                        },
                        eval_questions=self._indicator_questions(f["title"], value),
                    )
                )
        return chunks, all_atomic_facts

    def _build_indicator_inventory(self, rule: dict, f: dict, all_facts: list[dict]) -> dict:
        suspicious = [x for x in all_facts if not x["is_filter"]]
        filters = [x for x in all_facts if x["is_filter"]]
        return make_chunk(
            rule,
            "indicator_inventory",
            (
                f"Indicator inventory for {f['title']}.\n"
                f"Suspicious or monitored values:\n"
                f"{format_value([x['value'] for x in suspicious])}\n\n"
                f"Filtered legitimate values:\n"
                f"{format_value([x['value'] for x in filters])}"
            ),
            eval_questions=[
                f"List all monitored values in {f['title']}.",
                f"What indicators are monitored by {f['title']}?",
                f"Which values are excluded by {f['title']}?",
            ],
        )

    def _build_investigation_guidance(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "investigation_guidance",
            (
                f"Investigation guidance for alerts from {f['title']}.\n"
                f"Investigate the entity, user, process, host, timestamp, "
                f"and event context that matched the Sigma rule.\n"
                f"Review whether the matched values are expected in the environment."
            ),
            eval_questions=[
                f"How should an analyst investigate alerts from {f['title']}?",
                f"What context matters for {f['title']} alerts?",
                f"Que faut-il vérifier lors d'une alerte {f['title']} ?",
            ],
        )

    def _build_false_positive_context(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "false_positive_context",
            (
                f"False positive context for {f['title']}.\n"
                f"False positives:\n{format_value(f['falsepositives'])}\n"
                f"Common benign causes may include administrative activity, "
                f"automation, package managers, security tools."
            ),
            eval_questions=[
                f"What false positives can occur for {f['title']}?",
                f"How can false positives be reduced for {f['title']}?",
                f"Quels faux positifs sont attendus pour {f['title']} ?",
            ],
        )

    def _build_natural_language_queries(self, rule: dict, f: dict) -> dict:
        return make_chunk(
            rule,
            "natural_language_queries",
            (
                f"Natural language retrieval hints for {f['title']}.\n"
                f"This rule is relevant for questions such as:\n"
                f"- What does {f['title']} detect?\n"
                f"- Which detection fields and values are used?\n"
                f"- What logsource is required?"
            ),
            eval_questions=[
                f"Which rule detects behavior described by {f['title']}?",
                f"What fields are used by {f['title']}?",
                f"What ATT&CK mapping is associated with {f['title']}?",
            ],
        )

    def _build_backend_mapping_hints(self, rule: dict, f: dict) -> dict:
        lines: list[str] = []
        for det_name, det_val in f["detection"].items():
            if det_name == "condition":
                continue
            role = "exclusion" if det_name.startswith("filter") else "selection"
            lines.append(f"  - {det_name} ({role}): {format_value(det_val)}")
        summary = "\n".join(lines) if lines else "N/A"
        return make_chunk(
            rule,
            "backend_mapping_hints",
            (
                f"Backend mapping hints for {f['title']}.\n"
                f"The detection fields should be mapped to the corresponding "
                f"SIEM, EDR, or log backend schema.\n"
                f"Operators from Sigma such as contains, startswith, endswith, "
                f"all, and equals should be preserved during translation.\n"
                f"Condition: {f['condition']}\n\n"
                f"Detection blocks:\n{summary}"
            ),
            eval_questions=[
                f"What fields should be mapped for {f['title']}?",
                f"How should {f['title']} be translated to a SIEM query?",
                f"What operators are used in {f['title']}?",
            ],
        )

    def _enrich_chunks(self, chunks: list[dict], llm_client: LLMClientLike) -> list[dict]:
        enriched: list[dict] = []
        for chunk in chunks:
            try:
                result = enrich_by_llm(chunk["text"], llm_client)
            except Exception:
                logger.debug("LLM enrichment failed for chunk %s", chunk.get("chunk_type", "?"))
                result = {"summary": None, "keywords": None, "error": "enrichment_failed"}
            summary = result.get("summary") or ""
            keywords = result.get("keywords") or ""
            if summary or keywords:
                enrichment = "\n\n---\n"
                if summary:
                    enrichment += f"Summary: {summary}\n\n"
                if keywords:
                    enrichment += f"Keywords: {keywords}\n"
                chunk["text"] = chunk["text"] + enrichment
            enriched.append(chunk)
        return enriched

    def _chunk_rule(self, rule: dict, llm_client: LLMClientLike | None = None) -> list[dict]:
        f = self._extract_fields(rule)
        chunks = self._assemble_chunks(rule, f)

        if llm_client is not None:
            chunks = self._enrich_chunks(chunks, llm_client)

        return chunks

    def _assemble_chunks(self, rule: dict, f: dict) -> list[dict]:
        """Assemble all chunks for a Sigma rule.

        Args:
            rule: The raw Sigma rule dict.
            f: Extracted fields dict from ``_extract_fields()``.

        Returns:
            List of chunk dicts ready for document conversion.
        """
        chunks: list[dict] = [
            self._build_executive_summary(rule, f),
            self._build_metadata_lifecycle(rule, f),
            self._build_logsource_context(rule, f),
        ]

        if (attack := self._build_mitre_attack_mapping(rule, f)) is not None:
            chunks.append(attack)

        chunks.append(self._build_detection_condition(rule, f))

        det_chunks, all_facts = self._build_detection_block_chunks(rule, f)
        chunks.extend(det_chunks)

        chunks.extend(
            [
                self._build_indicator_inventory(rule, f, all_facts),
                self._build_investigation_guidance(rule, f),
                self._build_false_positive_context(rule, f),
                self._build_natural_language_queries(rule, f),
                self._build_backend_mapping_hints(rule, f),
            ]
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
            excluded_embed_metadata_keys=["chunk_type", "source_file"],
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


# Register SigmaChunker for rich mode.
TransformRegistry.register(SigmaChunker)


# ------------------------------------------------------------------
# Backwards-compatible function
# ------------------------------------------------------------------


def chunk_sigma_rules_rich(rule: dict) -> list[dict]:
    """Legacy entry-point: chunk a single Sigma rule dict into enriched chunks.

    Kept for backwards compatibility. New code should use ``SigmaChunker.process()``
    via the DocumentTransform contract.
    """
    chunker = SigmaChunker()
    return chunker._chunk_rule(rule)
