"""Admin prompts management."""

from __future__ import annotations

import re
import uuid

from src.back.database import DatabaseService

_prompts: dict[str, Prompt] = {}


def _load_all() -> dict[str, Prompt]:
    db = DatabaseService.get_instance()
    if db is None:
        return {}
    prompts_list = db.get_prompts()
    return {
        p["id"]: Prompt(
            prompt_id=p["id"],
            name=p["name"],
            description=p.get("description", ""),
            content=p["content"],
            is_active=p.get("is_active", False),
        )
        for p in prompts_list
    }


def _save_all(prompts: dict[str, Prompt]) -> None:
    db = DatabaseService.get_instance()
    for p in prompts.values():
        db.upsert_prompt(
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "content": p.content,
                "is_active": p.is_active,
            }
        )


def _ensure_loaded() -> None:
    global _prompts
    _prompts = _load_all()


def validate_name(name: str) -> None:
    """Validates that the name is kebab-case and max 25 characters."""
    if len(name) > 25:
        raise ValueError("Name must be 25 characters or less.")
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", name):
        raise ValueError("Name must be in kebab-case (e.g., 'my-prompt').")


def validate_description(description: str) -> None:
    """Validates that the description is max 100 characters."""
    if len(description) > 100:
        raise ValueError("Description must be 100 characters or less.")


class Prompt:
    """Represents a system prompt."""

    def __init__(
        self,
        prompt_id: str,
        name: str,
        description: str,
        content: str,
        is_active: bool = False,
    ):
        self.id = prompt_id
        self.name = name
        self.description = description
        self.content = content
        self.is_active = is_active

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Prompt:
        return cls(
            prompt_id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            content=data["content"],
            is_active=data.get("is_active", False),
        )


def list_prompts() -> list[dict]:
    """List all prompts."""
    _ensure_loaded()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "is_active": p.is_active,
        }
        for p in _prompts.values()
    ]


def get_prompt_content(prompt_id: str) -> str | None:
    """Get prompt content by ID."""
    _ensure_loaded()
    prompt = _prompts.get(prompt_id)
    return prompt.content if prompt else None


def get_prompt_description(prompt_id: str) -> str | None:
    """Get prompt description by ID."""
    _ensure_loaded()
    prompt = _prompts.get(prompt_id)
    return prompt.description if prompt else None


def get_prompt_by_id(prompt_id: str) -> Prompt | None:
    """Get a prompt by ID."""
    _ensure_loaded()
    return _prompts.get(prompt_id)


def get_prompt_by_name(name: str) -> Prompt | None:
    """Get a prompt by its name."""
    _ensure_loaded()
    for prompt in _prompts.values():
        if prompt.name == name:
            return prompt
    return None


def get_active_prompt() -> Prompt | None:
    """Get the active prompt."""
    _ensure_loaded()
    for prompt in _prompts.values():
        if prompt.is_active:
            return prompt
    return None


def add_prompt(name: str, description: str, content: str) -> Prompt:
    """Add a new prompt."""
    validate_name(name)
    validate_description(description)

    prompt = Prompt(
        prompt_id=str(uuid.uuid4()), name=name, description=description, content=content
    )
    _prompts[prompt.id] = prompt
    _save_all(_prompts)
    return prompt


def update_prompt(
    prompt_id: str, name: str = None, description: str = None, content: str = None
) -> bool:
    """Update an existing prompt."""
    _ensure_loaded()
    prompt = _prompts.get(prompt_id)
    if not prompt:
        return False

    if name is not None:
        validate_name(name)
        prompt.name = name
    if description is not None:
        validate_description(description)
        prompt.description = description
    if content is not None:
        prompt.content = content

    _save_all(_prompts)
    return True


def set_active_prompt(prompt_id: str) -> bool:
    """Set a prompt as active."""
    _ensure_loaded()
    for p in _prompts.values():
        p.is_active = p.id == prompt_id
    _save_all(_prompts)
    return prompt_id in _prompts


def delete_prompt(prompt_id: str) -> None:
    """Delete a prompt by ID."""
    _ensure_loaded()
    if prompt_id in _prompts:
        del _prompts[prompt_id]
        db = DatabaseService.get_instance()
        if db:
            db.delete_prompt(prompt_id)
    else:
        raise ValueError(f"Prompt ID '{prompt_id}' not found")
