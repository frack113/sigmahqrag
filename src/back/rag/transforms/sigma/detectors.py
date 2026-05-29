
def is_sigma_rule(doc: dict) -> bool:
    """Determine si le fichier est une regle sigma

    Arg:
         - doc (dict): fichier yml
    Return:
        - bool: nature du fichier yml
        
    """
    return (
        isinstance(doc, dict)
        and "title" in doc
        and "id" in doc
        and "logsource" in doc
        and "detection" in doc
    )
