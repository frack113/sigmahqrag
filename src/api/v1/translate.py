"""Translate Sigma detection blocks into plain language."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from jinja2 import Environment, Undefined
from pydantic import BaseModel, Field

from src.back.services.rag_pipeline import RAGPipeline
from src.back.system_prompt import get_prompt_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/translate", tags=["v1-translate"])

DEFAULT_PROMPT_ID = "vulgarisation-english"
DEFAULT_TOP_K = 10
DEFAULT_TEMPERATURE = 0.1

# Stop sequences: the 14B model sometimes tries to hallucinate the rest of
# a Sigma rule (fields, level, logsource, ...) instead of giving the plain
# English translation. Hitting any of these strings ends generation
# immediately so the response stays focused on the translation.
SIGMA_YAML_STOP_SEQUENCES: list[str] = [
    "\ntitle:",
    "\nid:",
    "\nstatus:",
    "\ndescription:",
    "\nauthor:",
    "\ndate:",
    "\nmodified:",
    "\nreferences:",
    "\ntags:",
    "\nlevel:",
    "\nfields:",
    "\nlogsource:",
    "\nfalsepositives:",
    "\ndetection:",
    "\ncondition:",
]


def _render_safe(template_text: str, **kwargs: Any) -> str:
    """Render a Jinja2 template with user-controlled content safely.

    Uses ``jinja2.Undefined`` to prevent template injection: any
    ``{{ user_variable }}`` in user input will render as the literal
    string ``Undefined`` instead of being evaluated as template syntax.
    This protects against prompt injection via Sigma rules that happen
    to contain Jinja2-like syntax (e.g. Windows variables).
    """
    env = Environment(undefined=Undefined)
    template = env.from_string(template_text)
    # Render with defaults that produce safe literal output
    defaults: dict[str, Any] = {
        "search_results": kwargs.get("search_results", ""),
        "question": kwargs.get("question", ""),
    }
    return template.render(defaults)


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
async def translate_detection(req: TranslateDetectionRequest) -> JSONResponse:
    """Translate a Sigma ``detection`` block into plain language.

    The endpoint reuses the RAG pipeline: optionally searches the spec
    collection, then renders the chosen system prompt with the YAML as
    the user question and streams the LLM answer back as text.
    """
    yaml_text = req.yaml.strip()
    if not yaml_text:
        return JSONResponse(
            status_code=400,
            content={"error": "yaml is required and cannot be empty"},
        )

    rag = RAGPipeline()

    try:
        if req.use_search:
            results: list[dict[str, Any]] = await rag.search_engine.search(
                yaml_text, top_k=DEFAULT_TOP_K
            )
            translation: str = await rag.answer_search_query(
                query=yaml_text,
                search_results=results,
                system_prompt_id=req.prompt_id,
                temperature=DEFAULT_TEMPERATURE,
                bypass_cache=req.bypass_cache,
                use_chat=req.use_chat,
                stop=SIGMA_YAML_STOP_SEQUENCES,
            )
            citations: list[str] = [
                rag.search_engine.get_citation(r)
                for r in results[:5]
                if rag.search_engine.get_citation(r)
            ]
        else:
            prompt_obj = get_prompt_by_id(req.prompt_id)
            if prompt_obj is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Prompt '{req.prompt_id}' not found"},
                )

            # Use safe rendering to prevent Jinja2 injection from user YAML.
            # The prompt template expects {{ search_results }} and {{ question }}
            # but we render question as user message content, so only
            # search_results needs to be interpolated.
            prompt = _render_safe(prompt_obj.content, search_results="(no reference)")

            if req.use_chat:
                translation = await rag.llm_client.chat(
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": (
                                "Translate the detection above into plain English.\n\n"
                                f"Detection YAML:\n{yaml_text}"
                            ),
                        },
                    ],
                    temperature=DEFAULT_TEMPERATURE,
                    stop=SIGMA_YAML_STOP_SEQUENCES,
                )
            else:
                translation = await rag.llm_client.generate(
                    prompt=f"{prompt}\n\nInput to translate:\n{yaml_text}",
                    temperature=DEFAULT_TEMPERATURE,
                )
            citations = []

        return JSONResponse(
            content={
                "translation": translation,
                "citations": citations,
                "prompt_id": req.prompt_id,
            }
        )
    except Exception as e:
        logger.error("translate_detection failed: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred"},
        )
