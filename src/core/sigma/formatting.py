from typing import Any


def format_value(value: Any, indent: int = 0) -> str:
    """Convertit en texte indenté.

    Args:
        - value (Any): Valeur à formater (Dictionnaire, liste; ect...)
        - indent (int): Nbr espaces d'indentation
    Return:
        - str: Chaine de caractères representant value sous forme de liste

    """
    prefix = " " * indent
    lines: list[str] = []

    if isinstance(value, dict):
        for key, val in value.items():
            lines.append(f"{prefix}- {key}:")
            lines.append(format_value(val, indent + 2))

    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(format_value(item, indent))
            else:
                lines.append(f"{prefix}- {item}")

    else:
        lines.append(f"{prefix}- {value}")

    return "\n".join(lines)
