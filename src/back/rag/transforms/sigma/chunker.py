from .chunk_factory import make_chunk
from .flattening import flatten_detection_values, split_field_operator
from .formatting import format_value


def chunk_sigma_rules_rich(rule: dict) -> list[dict]:
    """Decoupe une regle Sigma en plusieurs chunks enrichis pour le RAG.

    Arg:
        - rule (dict): regle sigma contenant metadata, logsource, detection, faux positifs, refs et tags
    Return:
        - list[dict]: liste de chunks decrivant la regle
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

# ------------------------------------------------------------------
# Chunk: Executive summary
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "executive_summary",
            f"""
Sigma rule: {title}
Rule ID: {rule_id}
Purpose: {description}
This rule is designed for {product} logs with category={category} and service={service}.
Severity: {level}. Status: {status}.
Main detection logic: {condition}
            """,
            eval_questions=[
                f"What does the Sigma rule {title} detect?",
                f"Explain the purpose of {title}.",
                f"Quelle est l'intention de la règle Sigma {title} ?",
            ],
        )
    )


# ------------------------------------------------------------------
# Chunk: Rule metadata and lifecycle
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "rule_metadata_lifecycle",
            f"""
Rule metadata for {title}.
Rule ID: {rule_id}
Author: {author}
Created date: {date}
Modified date: {modified}
Status: {status}
Level: {level}
References:
{format_value(references)}
            """,
            eval_questions=[
                f"Who authored {title}?",
                f"When was {title} modified?",
                f"What is the lifecycle status of {title}?",
            ],
        )
    )

# ------------------------------------------------------------------
# Chunk: Logsource context
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "logsource_context",
            f"""
Logsource context for Sigma rule {title}.
Product: {product}
Category: {category}
Service: {service}
The rule expects telemetry from product={product}, category={category}, service={service}.
It should be mapped to fields that record relevant event attributes used by the detection block.
            """,
            eval_questions=[
                f"What logsource is required for {title}?",
                f"Which telemetry category does {title} use?",
                f"Sur quel produit la règle {title} s'applique-t-elle ?",
            ],
        )
    )

    attack_tags = [tag for tag in tags if str(tag).startswith("attack.")]

    if attack_tags:

# ------------------------------------------------------------------
# Chunk: MITRE ATT&CK mapping
# ------------------------------------------------------------------
        chunks.append(
            make_chunk(
                rule,
                "mitre_attack_mapping",
                f"""
MITRE ATT&CK mapping for {title}.
Tags:
{format_value(attack_tags)}
This chunk describes the ATT&CK tactics and techniques associated with this Sigma rule.
                """,
                {"attack_tags": attack_tags},
                [
                    f"What MITRE ATT&CK techniques are mapped to {title}?",
                    f"Which ATT&CK tactic is relevant to {title}?",
                    f"What Sigma rule maps to {', '.join(map(str, attack_tags))}?",
                ],
            )
        )

# ------------------------------------------------------------------
# Chunk: Detection condition
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "detection_condition",
            f"""
Detection condition for {title}.
Condition: {condition}
Interpretation: this condition defines how selection and filter blocks are combined to trigger the rule.
            """,
            {"condition": condition},
            [
                f"What is the Sigma condition of {title}?",
                f"How are selections and filters combined in {title}?",
                f"Que signifie la condition de détection de {title} ?",
            ],
        )
    )

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

# ------------------------------------------------------------------
# Chunk: Detection selection/filter block
# ------------------------------------------------------------------
        chunks.append(
            make_chunk(
                rule,
                chunk_type,
                f"""
Detection block {detection_name} in Sigma rule {title}.
Block role: {"exclusion / false positive reduction" if is_filter else "positive detection indicator"}
Raw block:
{format_value(detection_value)}
                """,
                {
                    "detection_name": detection_name,
                    "is_filter": is_filter,
                },
                [
                    f"What does detection block {detection_name} contain?",
                    f"Which values are checked in {detection_name}?",
                    f"Is {detection_name} a detection or a filter?",
                ],
            )
        )

        by_field_operator: dict[str, list] = {}

        for fact in facts:
            by_field_operator.setdefault(fact["field_operator"], []).append(fact["value"])

        for field_operator, values in by_field_operator.items():
            field, operator = split_field_operator(field_operator)

# ------------------------------------------------------------------
# Chunk: Field/operator group
# ------------------------------------------------------------------
            chunks.append(
                make_chunk(
                    rule,
                    "field_operator_group",
                    f"""
Field/operator group in {title}.
Detection block: {detection_name}
Field: {field}
Operator: {operator}
Role: {"filter/exclusion" if is_filter else "indicator/selection"}
Values:
{format_value(values)}
                    """,
                    {
                        "detection_name": detection_name,
                        "field": field,
                        "operator": operator,
                        "is_filter": is_filter,
                    },
                    [
                        f"What values does {title} check for field {field}?",
                        f"What operator is used on {field} in {title}?",
                        f"Which rule contains {field_operator}?",
                    ],
                )
            )

        for fact in facts:
            field, operator = split_field_operator(fact["field_operator"])
            value = fact["value"]

# ------------------------------------------------------------------
# Chunk: Atomic indicator
# ------------------------------------------------------------------
            chunks.append(
                make_chunk(
                    rule,
                    "atomic_indicator",
                    f"""
Atomic Sigma indicator for {title}.
Detection block: {detection_name}
Field: {field}
Operator: {operator}
Value: {value}
Role: {"legitimate exclusion / filter" if is_filter else "suspicious or monitored indicator"}
A match on this value contributes to the rule condition: {condition}
                    """,
                    {
                        "detection_name": detection_name,
                        "field": field,
                        "operator": operator,
                        "value": value,
                        "is_filter": is_filter,
                    },
                    [
                        f"Which Sigma rule detects {value}?",
                        f"Is {value} suspicious or filtered in {title}?",
                        f"What field contains {value} in {title}?",
                    ],
                )
            )

    suspicious_values = [fact for fact in all_atomic_facts if not fact["is_filter"]]
    filter_values = [fact for fact in all_atomic_facts if fact["is_filter"]]

# ------------------------------------------------------------------
# Chunk: Indicator inventory
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "indicator_inventory",
            f"""
Indicator inventory for {title}.
Suspicious or monitored values:
{format_value([fact["value"] for fact in suspicious_values])}

Filtered legitimate values:
{format_value([fact["value"] for fact in filter_values])}
            """,
            eval_questions=[
                f"List all monitored values in {title}.",
                f"What indicators are monitored by {title}?",
                f"Which values are excluded by {title}?",
            ],
        )
    )
    
# ------------------------------------------------------------------
# Chunk: Investigation guidance
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "investigation_guidance",
            f"""
Investigation guidance for alerts from {title}.
Investigate the entity, user, process, host, timestamp, and event context that matched the Sigma rule.
Review whether the matched values are expected in the environment.
Check whether the event indicates persistence, execution, privilege escalation, defense evasion, discovery, or another suspicious behavior.
Baseline normal activity and tune filters accordingly.
            """,
            eval_questions=[
                f"How should an analyst investigate alerts from {title}?",
                f"What context matters for {title} alerts?",
                f"Que faut-il vérifier lors d'une alerte {title} ?",
            ],
        )
    )
    
# ------------------------------------------------------------------
# Chunk: False positive context
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "false_positive_context",
            f"""
False positive context for {title}.
False positives:
{format_value(falsepositives)}
Common benign causes may include administrative activity, automation, package managers, security tools, configuration management, cloud agents, or expected system maintenance.
The rule should be tuned using baselining and environment-specific allowlists.
References:
{format_value(references)}
            """,
            eval_questions=[
                f"What false positives can occur for {title}?",
                f"How can false positives be reduced for {title}?",
                f"Quels faux positifs sont attendus pour {title} ?",
            ],
        )
    )
    
# ------------------------------------------------------------------
# Chunk: Natural language queries
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "natural_language_queries",
            f"""
Natural language retrieval hints for {title}.
This rule is relevant for questions such as:
- What does the Sigma rule {title} detect?
- Which detection fields and values are used by {title}?
- What logsource is required by {title}?
- What false positives are expected for {title}?
- Which MITRE ATT&CK tags are mapped to {title}?
- How should an analyst investigate alerts from {title}?
            """,
            eval_questions=[
                f"Which rule detects behavior described by {title}?",
                f"What fields are used by {title}?",
                f"What ATT&CK mapping is associated with {title}?",
                f"Quelle règle Sigma correspond à {title} ?",
            ],
        )
    )

# ------------------------------------------------------------------
# Chunk: Backend mapping hints
# ------------------------------------------------------------------
    chunks.append(
        make_chunk(
            rule,
            "backend_mapping_hints",
            f"""
Backend mapping hints for {title}.
The detection fields should be mapped to the corresponding SIEM, EDR, or log backend schema.
Operators from Sigma such as contains, startswith, endswith, all, and equals should be preserved during translation.
The condition should be preserved exactly where possible:
{condition}
            """,
            eval_questions=[
                f"What fields should be mapped for {title}?",
                f"How should {title} be translated to a SIEM query?",
                f"What operators are used in {title}?",
            ],
        )
    )

    return chunks
