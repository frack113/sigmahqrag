def make_chunk(
    rule: dict,
    chunk_type: str,
    text: str,
    extra_meta: dict | None = None,
    eval_questions: list[str] | None = None,
) -> dict:
    """Creer un chunk structure a partir d une regle sigma

    Args:
        - rule (dict): regle sigma
        - chunk_type (str): type de chunk genere
        - text (str): texte du chunk
        - extra_meta (dict): metadata supp
        - eval_questions: questions d'eval associee au chunk
    Return:
        - dict: Dictionnaire contenant le texte nettoye, avec metadata, et questions evals et ground_truth

    """

    logsource = rule.get("logsource", {})
    metadata = {
        "rule_id": rule.get("id"),
        "title": rule.get("title", "Untitled Sigma rule"),
        "level": rule.get("level", "unknown"),
        "status": rule.get("status", "unknown"),
        "tags": rule.get("tags", []),
        "product": logsource.get("product", "unknown"),
        "category": logsource.get("category", "unknown"),
        "service": logsource.get("service", "unknown"),
        "chunk_type": chunk_type,
        "author": rule.get("author", ""),
        "description": rule.get("description", ""),
        "date": rule.get("date", ""),
        "modified": rule.get("modified", ""),
        "falsepositives": rule.get("falsepositives", []),
        "related": rule.get("related", []),
        "name": rule.get("name", ""),
        "references": rule.get("references", []),
        **(extra_meta or {}),
    }

    clean_text = text.strip()

    return {
        "chunk_type": chunk_type,
        "text": clean_text,
        "metadata": metadata,
        "eval_questions": eval_questions or [],
        "ground_truth": clean_text,
    }
