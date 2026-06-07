"""Translate Sigma detection blocks into plain language."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.application.chat.rag import RAGPipeline
from src.application.sigma.translate import translate_detection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/translate", tags=["v1-translate"])

DEFAULT_PROMPT_ID = "vulgarisation-english"


class TranslateDetectionRequest(BaseModel):
    """Request body for translating a Sigma detection block."""

    yaml: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Sigma detection block (YAML or plain text)",
    )
    prompt_id: str = Field(
        DEFAULT_PROMPT_ID,
        max_length=64,
        description="System prompt ID to use for translation",
    )
    use_search: bool = Field(
        True,
        description="Run RAG search against the Sigma spec to enrich the prompt",
    )
    bypass_cache: bool = Field(
        False,
        description="Skip RAG response cache (force a fresh LLM generation)",
    )
    use_chat: bool = Field(
        True,
        description="Use /v1/chat/completions instead of raw /v1/completions. "
        "Chat mode is more reliable for instruction models on YAML inputs.",
    )


@router.post("/detection")
async def translate_detection_endpoint(req: TranslateDetectionRequest) -> JSONResponse:
    """Translate a Sigma ``detection`` block into plain language."""
    yaml_text = req.yaml.strip()
    if not yaml_text:
        return JSONResponse(
            status_code=400,
            content={"error": "yaml is required and cannot be empty"},
        )

    rag = RAGPipeline()

    try:
        translation = await translate_detection(
            yaml_text,
            rag,
            prompt_id=req.prompt_id,
            use_chat=req.use_chat,
        )

        # Clear KV cache to avoid polluting the shared llama-server slot
        try:
            await rag.llm_client.erase_slot_cache()
        except Exception:
            logger.warning("Failed to clear KV cache after translate")

        if not translation:
            return JSONResponse(
                status_code=500,
                content={"error": "Translation failed"},
            )

        return JSONResponse(
            content={
                "translation": translation,
                "citations": [],
                "prompt_id": req.prompt_id,
            }
        )
    except Exception as e:
        logger.error("translate_detection failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred"},
        )
