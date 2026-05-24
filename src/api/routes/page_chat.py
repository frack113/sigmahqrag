"""Chat page route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.front import TEMPLATES_DIR
from src.shared import LLM_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-chat"])


@router.get("/")
@router.get("/chat")
async def chat_page(request: Request):
    """Serve the chat page with Jinja2 template."""
    models = _get_installed_llm_models()
    prompts = _get_prompts()
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"models": models, "prompts": prompts},
    )


def _get_installed_llm_models() -> list[dict]:
    """Fetch installed LLM models (repo_id + filename + size)."""
    try:
        from src.api.dependencies import get_database_service, get_unified_registry

        db = get_database_service()
        reg = get_unified_registry()
        reg.sync_llm_folder(LLM_DIR, db)
        llms = reg.list_llms(db)

        model_list = []
        for repo_id, data in llms.items():
            for filename, info in data.get("files", {}).items():
                model_list.append(
                    {
                        "repo_id": repo_id,
                        "filename": info.get("filename", filename),
                        "size_mb": round((info.get("file_size", 0) or 0) / (1024 * 1024), 1),
                    }
                )
        return model_list
    except Exception:
        return []


def _get_prompts() -> list[dict]:
    """Fetch system prompts from the database."""
    try:
        from src.back.system_prompt import list_prompts

        return list_prompts()
    except Exception:
        return []
