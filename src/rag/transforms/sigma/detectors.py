from src.shared.schemas.sigma_rule import is_sigma_rule as is_sigma_rule_fn

__all__ = ["is_sigma_rule"]


def is_sigma_rule(doc: dict) -> bool:  # type: ignore[no-redef]
    """Determine si le fichier est une regle sigma.

    Re-export of the canonical ``is_sigma_rule`` from
    ``src.shared.schemas.sigma_rule`` to maintain the original
    call-site API (dict-only).
    """
    return is_sigma_rule_fn(doc)
