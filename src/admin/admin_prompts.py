"""System prompt management for RAG chat."""

from __future__ import annotations

import logging
import tomllib
from typing import Any

import tomli_w

from src.config import CONFIG_FILE

logger = logging.getLogger(__name__)


def _load_toml() -> dict[str, Any]:
    """Load the TOML config file."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load TOML config from {CONFIG_FILE}: {e}")
        return {}


def _save_toml(config: dict[str, Any]) -> None:
    """Write the TOML config file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(config, f)


def list_prompts() -> list[dict[str, str]]:
    """List all configured system prompts.

    Returns:
        List of dicts with keys: name, content
    """
    config = _load_toml()
    prompts_section = config.get("system_prompts", {})

    results = []
    for name in sorted(prompts_section.keys()):
        if name == "active":
            continue
        entry = prompts_section[name]
        if isinstance(entry, str):
            results.append({"name": name, "content": entry})
        elif isinstance(entry, dict) and "content" in entry:
            results.append({"name": name, "content": entry["content"]})

    return results


def get_active_prompt() -> str | None:
    """Get the currently active system prompt name.

    Returns:
        Prompt name or None if not set.
    """
    config = _load_toml()
    active = config.get("system_prompts", {}).get("active")
    if not isinstance(active, str):
        return None
    return active


def get_prompt_content(name: str) -> str | None:
    """Get the content of a named system prompt.

    Args:
        name: Prompt identifier

    Returns:
        Prompt text or None if not found.
    """
    config = _load_toml()
    prompts_section = config.get("system_prompts", {})

    entry = prompts_section.get(name)
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        content = entry.get("content")
        if isinstance(content, str):
            return content
    return None


def get_active_prompt_content() -> str | None:
    """Get the content of the active system prompt.

    Returns:
        Prompt text or None if no active prompt is set.
    """
    active = get_active_prompt()
    if active is None:
        return None
    return get_prompt_content(active)


def add_prompt(name: str, content: str) -> dict[str, Any]:
    """Add or update a system prompt.

    Args:
        name: Unique identifier (kebab-case recommended)
        content: Prompt text

    Returns:
        Dict with success status and message.
    """
    if not name.strip():
        return {"success": False, "message": "Name cannot be empty"}
    if name == "active":
        return {"success": False, "message": "'active' is a reserved key"}
    if not content or not content.strip():
        return {"success": False, "message": "Content cannot be empty"}

    config = _load_toml()
    if "system_prompts" not in config:
        config["system_prompts"] = {}

    prompts_section = config["system_prompts"]
    already_exists = name in prompts_section
    prompts_section[name] = content

    try:
        _save_toml(config)
        if already_exists:
            logger.info(f"Updated prompt '{name}'")
            return {"success": True, "message": f"Prompt '{name}' updated"}
        else:
            logger.info(f"Added prompt '{name}'")
            return {"success": True, "message": f"Prompt '{name}' saved"}
    except Exception as e:
        logger.error(f"Failed to save prompt '{name}': {e}")
        return {"success": False, "message": str(e)}


def delete_prompt(name: str) -> dict[str, Any]:
    """Delete a system prompt.

    Args:
        name: Prompt identifier to remove

    Returns:
        Dict with success status and message.
    """
    config = _load_toml()
    prompts_section = config.get("system_prompts", {})

    if "active" in prompts_section and prompts_section["active"] == name:
        del prompts_section["active"]

    if name not in prompts_section:
        return {"success": False, "message": f"Prompt '{name}' not found"}

    del prompts_section[name]

    try:
        _save_toml(config)
        logger.info(f"Deleted prompt '{name}'")
        return {"success": True, "message": f"Prompt '{name}' deleted"}
    except Exception as e:
        logger.error(f"Failed to delete prompt '{name}': {e}")
        return {"success": False, "message": str(e)}


def set_active_prompt(name: str) -> dict[str, Any]:
    """Set a prompt as the active system prompt.

    Args:
        name: Prompt identifier to activate

    Returns:
        Dict with success status and message.
    """
    config = _load_toml()
    prompts_section = config.get("system_prompts", {})

    if "active" not in prompts_section:
        config["system_prompts"] = dict(prompts_section)
        prompts_section = config["system_prompts"]

    name_key = name
    if name_key == "active":
        return {"success": False, "message": "'active' is a reserved key"}

    if name_key not in prompts_section:
        return {"success": False, "message": f"Prompt '{name}' not found"}

    prompts_section["active"] = name_key

    try:
        _save_toml(config)
        logger.info(f"Set active prompt to '{name}'")
        return {"success": True, "message": f"Active prompt set to '{name}'"}
    except Exception as e:
        logger.error(f"Failed to set active prompt: {e}")
        return {"success": False, "message": str(e)}
