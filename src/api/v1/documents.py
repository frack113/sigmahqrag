"""Documents API v1."""

from __future__ import annotations

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.back.database.service import DatabaseService
from src.back.documents.models import IngestRequest
from src.back.documents.sigma_ref_downloader import download_references
from src.back.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES
from src.shared.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["v1-documents"])


@router.post("/index-sigma-ref")
async def index_sigma_ref(
    request: IngestRequest | None = None,
) -> JSONResponse:
    """Download and prepare Sigma reference documents."""
    cfg = get_config()
    rules_dir = cfg.paths_github_dir
    output_dir = cfg.paths_sigma_ref_docs_dir

    try:
        db = DatabaseService.get_instance()
        selected_dirs: list[str] = []
        if request and request.selected_dirs:
            selected_dirs = request.selected_dirs
        summary = download_references(
            rules_dir=rules_dir,
            output_dir=output_dir,
            db=db,
            supported_types=SUPPORTED_REFERENCE_DOC_TYPES,
            selected_dirs=selected_dirs,
        )
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error("Failed to index sigma ref: %s", e, exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
