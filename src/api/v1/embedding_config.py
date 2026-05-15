"""Embedding config API v1."""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.back.embedding_config import EmbeddingTypeConfig
from src.back.utils.identify_file_type import FileType

logger = logging.getLogger(__name__)

MODEL_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")
VALID_TYPE_KEYS = {ft.value for ft in FileType}

router = APIRouter(prefix="/api/v1/embedding-config", tags=["v1-embedding-config"])

_config_manager = EmbeddingTypeConfig()


@router.get("")
async def get_embedding_config() -> JSONResponse:
    """Get the full embedding type configuration."""
    config = _config_manager.load()
    return JSONResponse(content=json.loads(json.dumps(config, default=str)))


@router.put("/{type_key}")
async def update_type_config(type_key: str, body: dict) -> JSONResponse:
    """Update or remove a type's embedding config.

    Sending model="" removes the type from config.
    Accepts a generic dict for forward-compatibility.
    """
    if not type_key.strip():
        return JSONResponse(
            status_code=400, content={"error": "type_key must not be empty"}
        )

    if type_key not in VALID_TYPE_KEYS:
        return JSONResponse(
            status_code=400, content={"error": f"Unknown type_key: {type_key}"}
        )

    if "model" not in body:
        return JSONResponse(status_code=400, content={"error": "model is required"})

    model = (body.get("model") or "").strip()
    if model and not MODEL_ID_RE.match(model):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid model ID format (expected: org/model)"},
        )

    config = _config_manager.update_type(type_key, body)
    if config is None:
        return JSONResponse(status_code=500, content={"error": "Failed to save config"})
    return JSONResponse(content=json.loads(json.dumps(config, default=str)))
