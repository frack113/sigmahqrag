"""Documents API v1."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.back.database.service import DatabaseService
from src.back.documents.indexing import index_sigma_rules
from src.back.documents.models import (
    IngestRequest,
    IngestResult,
)
from src.back.documents.sigma_ref_downloader import download_references
from src.back.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES
from src.back.documents.parser import parse_sigma_rule, scan_directory
from src.back.documents.validator import validate_sigma_rule

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["v1-documents"])


def _validate_directory_path(directory: str, base_dir: str) -> str:
    """Validate and resolve a directory path to prevent path traversal."""
    resolved = Path(directory).resolve()
    base = Path(base_dir).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Directory '{directory}' is not within the allowed base directory")
    return str(resolved)


@router.post("/ingest")
async def ingest_sigma_rules(
    request: IngestRequest | None = None,
) -> JSONResponse:
    """Ingest Sigma rules from configured directory.

    Args:
        request: Optional directory/recursive parameters.
        mode: 'flat' (default) or 'rich' chunking mode.

    Returns:
        JSONResponse with ingestion results.
    """
    # Read parameters from request body
    mode = request.mode if request and request.mode else "flat"
    directory = request.directory if request else None
    recursive = request.recursive if request and request.recursive is not None else True

    # Scan both github dir (Sigma rules) and local_documents_dir (reference docs)
    if directory:
        directories = [directory]
    else:
        from src.shared.config import get_config

        cfg = get_config()
        directories = [cfg.paths_github_dir, cfg.local_documents_path]

    all_files: list[str] = []
    for d in directories:
        files = scan_directory(d, recursive=recursive)
        logger.info(f"Found {len(files)} YAML files in {d}")
        all_files.extend(files)

    files = sorted(all_files)
    logger.info(f"Found {len(files)} YAML files total")

    results: list[IngestResult] = []
    successful_rules = []

    for file_path in files:
        try:
            rule = parse_sigma_rule(file_path)
            if not rule:
                results.append(
                    IngestResult(
                        file=file_path,
                        success=False,
                        error="Failed to parse Sigma rule",
                    )
                )
                continue

            validation = validate_sigma_rule(rule)
            if not validation.valid:
                results.append(
                    IngestResult(
                        file=file_path,
                        success=False,
                        rule_id=rule.id,
                        error="; ".join(f"{e.field}: {e.message}" for e in validation.errors),
                    )
                )
                continue

            successful_rules.append(rule)
            results.append(
                IngestResult(
                    file=file_path,
                    success=True,
                    rule_id=rule.id,
                )
            )

        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
            results.append(
                IngestResult(
                    file=file_path,
                    success=False,
                    error="Failed to process rule file",
                )
            )

    if successful_rules:
        try:
            result = await index_sigma_rules(successful_rules, mode=mode)
            logger.info(
                f"Indexing complete: {result.get('indexed', 0)} chunks for {len(successful_rules)} rules"
            )
        except Exception as e:
            logger.error(f"Failed to index rules: {e}")

    return JSONResponse(
        content={
            "success": True,
            "total": len(results),
            "successful": len(successful_rules),
            "failed": len(results) - len(successful_rules),
            "mode": mode,
            "results": [r.model_dump() for r in results],
        }
    )


@router.post("/index-sigma-ref")
async def index_sigma_ref(
    request: IngestRequest | None = None,
) -> JSONResponse:
    """Download and prepare Sigma reference documents."""
    from src.shared.config import get_config

    cfg = get_config()
    rules_dir = os.environ.get("SIGMA_RULES_DIR", cfg.paths_sigma_rules_dir)
    output_dir = cfg.paths_sigma_ref_docs_dir

    try:
        db = DatabaseService.get_instance()
        summary = download_references(
            rules_dir=rules_dir,
            output_dir=output_dir,
            db=db,
            supported_types=SUPPORTED_REFERENCE_DOC_TYPES,
        )
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to index sigma ref: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"success": False, "error": "An internal error occurred"}
        )
