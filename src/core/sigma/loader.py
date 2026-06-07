from pathlib import Path
import yaml

from .detectors import is_sigma_rule


def load_sigma_rules(str_path: str) -> list[dict]:
    """Charge tout les fichiers yml/yaml du repo.

    Arg:
        - str_path (str): Chemin du repo
    Return:
        - list[dict]: liste contenant les fichiers yml/yaml

    """
    path = Path(str_path)

    if not path.exists():
        raise FileNotFoundError(path)

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = list(path.rglob("*.yml")) + list(path.rglob("*.yaml"))
    else:
        raise ValueError(f"Unsupported path type (not a file or directory): {path}")

    rules: list[dict] = []

    for file in files:
        with file.open(encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if doc is None:
                    continue
                if is_sigma_rule(doc):
                    rules.append(doc)

    return rules
