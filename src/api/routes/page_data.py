"""Data page routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.back.embedding_config import EmbeddingTypeConfig
from src.back.models import EmbeddingManager
from src.back.utils.identify_file_type import PUREMAGIC_TYPE_MAP, FileType

router = APIRouter(prefix="", tags=["pages"])
templates = Jinja2Templates(directory="src/front/templates")


def _build_filetype_extensions() -> dict[str, list[str]]:
    """Build reverse mapping from FileType value to list of extensions."""
    ext_map: dict[str, list[str]] = {}
    for ext, ftype in PUREMAGIC_TYPE_MAP.items():
        ext_map.setdefault(ftype.value, []).append(ext)
    ext_map.setdefault(FileType.SIGMA_RULE.value, []).extend([".yml", ".yaml"])
    ext_map.setdefault(FileType.MARKDOWN.value, []).append(".md")
    ext_map.setdefault(FileType.PLAIN_TEXT.value, []).append(".txt")
    ext_map.setdefault(FileType.YAML.value, []).extend([".yml", ".yaml"])
    ext_map.setdefault(FileType.JSON.value, []).append(".json")
    ext_map.setdefault(FileType.CSV.value, []).append(".csv")
    return ext_map


_FILE_TYPE_CACHE: list[dict] | None = None


def _serialize_file_types() -> list[dict]:
    """Serialize FileType enum members for Jinja consumption, with caching."""
    global _FILE_TYPE_CACHE
    if _FILE_TYPE_CACHE is not None:
        return _FILE_TYPE_CACHE
    ext_map = _build_filetype_extensions()
    _FILE_TYPE_CACHE = [
        {"name": ft.name, "value": ft.value, "extensions": ext_map.get(ft.value, [])}
        for ft in FileType
    ]
    return _FILE_TYPE_CACHE


@router.get("/data")
async def data_page(request: Request):
    """Serve the data sources page."""
    return templates.TemplateResponse(request=request, name="data/index.html")


@router.get("/data/github")
async def data_github_page(request: Request):
    """Serve the GitHub data source page."""
    return templates.TemplateResponse(request=request, name="data/github.html")


@router.get("/data/embedding")
async def data_embedding_page(request: Request):
    """Serve the embedding configuration page."""
    config_mgr = EmbeddingTypeConfig()
    config = config_mgr.load()
    safe_config = {k: v for k, v in config.items() if isinstance(v, dict)}

    # Supported document types (extend this list as more types are supported)
    supported_doc_types = {FileType.MARKDOWN.value}
    all_types = _serialize_file_types()
    file_types = [ft for ft in all_types if ft["value"] in supported_doc_types]

    # Get installed embedding models
    manager = EmbeddingManager()
    installed = await manager.list_installed()
    models = sorted(installed.keys()) if installed else []

    return templates.TemplateResponse(
        request=request,
        name="data/embedding.html",
        context={"file_types": file_types, "config": safe_config, "models": models},
    )
