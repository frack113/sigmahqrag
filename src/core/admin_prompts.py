"""Admin prompts management."""

from __future__ import annotations


class Prompt:
    """Represents a system prompt."""

    def __init__(self, id: str, name: str, content: str, is_active: bool = False):
        self.id = id
        self.name = name
        self.content = content
        self.is_active = is_active


_prompts: dict[str, Prompt] = {}


def list_prompts() -> list[dict]:
    """List all prompts."""
    return [{"id": p.id, "name": p.name, "is_active": p.is_active} for p in _prompts.values()]


def get_prompt_content(prompt_id: str) -> str | None:
    """Get prompt content by ID."""
    prompt = _prompts.get(prompt_id)
    return prompt.content if prompt else None


def get_active_prompt() -> Prompt | None:
    """Get the active prompt."""
    for prompt in _prompts.values():
        if prompt.is_active:
            return prompt
    return None


def get_active_prompt_content() -> str | None:
    """Get content of the active prompt."""
    active = get_active_prompt()
    return active.content if active else None


def add_prompt(name: str, content: str) -> Prompt:
    """Add a new prompt."""
    import uuid
    prompt = Prompt(id=str(uuid.uuid4()), name=name, content=content)
    _prompts[prompt.id] = prompt
    return prompt


def delete_prompt(prompt_id: str) -> bool:
    """Delete a prompt."""
    if prompt_id in _prompts:
        del _prompts[prompt_id]
        return True
    return False


def set_active_prompt(prompt_id: str) -> bool:
    """Set a prompt as active."""
    for p in _prompts.values():
        p.is_active = (p.id == prompt_id)
    return prompt_id in _prompts