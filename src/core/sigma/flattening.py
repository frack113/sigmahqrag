from typing import Any


def flatten_detection_values(value: Any, path: str = "") -> list[dict]:
    """Applatit value en une liste de faits (contenant le chemin du champ + valeur assocée)

    Arg:
        - value (Any): Valeur à parcourir
        - path (str): CHemin du champ courant
    Return:
        - list[dict]: Liste de dictionnaires contenant : champ et la valeur associee

    """

    facts: list[dict] = []

    if isinstance(value, dict):
        for key, val in value.items():
            new_path = f"{path}.{key}" if path else key
            facts.extend(flatten_detection_values(val, new_path))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                facts.extend(flatten_detection_values(item, path))
            else:
                facts.append({"field_operator": path, "value": item})
    else:
        facts.append({"field_operator": path, "value": value})

    return facts


def split_field_operator(field_operator: str) -> tuple[str, str]:
    """Separe un champ et son operateur

    Args:
        - field_operator (str): Chaine contenant le champ + operateur separer par '|'
    Return:
        - tuple[str, str]: champ et operateur avec 'equals' comme op par defaul

    """
    if "|" in field_operator:
        field, operator = field_operator.split("|", 1)
        return field, operator

    return field_operator, "equals"
