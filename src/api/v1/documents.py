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
from src.back.documents.parser import parse_sigma_rule, scan_directory
from src.back.documents.validator import validate_sigma_rule

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["v1-documents"])


def get_sigma_rules_dir() -> str:
    """Get Sigma rules directory from environment."""
    directory = os.environ.get("SIGMA_RULES_DIR")
    if not directory:
        raise ValueError("SIGMA_RULES_DIR environment variable not set")
    return directory


def _validate_directory_path(directory: str, base_dir: str) -> str:
    """Validate and resolve a directory path to prevent path traversal.

    Args:
        directory: User-provided directory path
        base_dir: Allowed base directory (from SIGMA_RULES_DIR)

    Returns:
        Resolved, validated absolute path

    Raises:
        ValueError: If path traversal is detected
    """
    resolved = Path(directory).resolve()
    base = Path(base_dir).resolve()
    if not str(resolved).startswith(str(base) + os.sep) and resolved != base:
        raise ValueError(f"Directory '{directory}' is not within the allowed base directory")
    return str(resolved)


@router.post("/ingest")
async def ingest_sigma_rules(
    request: IngestRequest | None = None,
) -> JSONResponse:
    """Ingest Sigma rules from configured directory."""
    directory = request.directory if request else None
    recursive = request.recursive if request else True

    if not directory:
        directory = get_sigma_rules_dir()
    else:
        try:
            base_dir = get_sigma_rules_dir()
            directory = _validate_directory_path(directory, base_dir)
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": str(e)},
            )

    logger.info(f"Scanning directory: {directory} (recursive={recursive})")

    files = scan_directory(directory, recursive=recursive)
    logger.info(f"Found {len(files)} YAML files")

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
                    error=str(e),
                )
            )

    if successful_rules:
        try:
            await index_sigma_rules(successful_rules)
        except Exception as e:
            logger.error(f"Failed to index rules: {e}")

    return JSONResponse(
        content={
            "success": True,
            "total": len(results),
            "successful": len(successful_rules),
            "failed": len(results) - len(successful_rules),
            "results": [r.model_dump() for r in results],
        }
    )


@router.post("/index-sigma-ref")
async def index_sigma_ref(
    request: IngestRequest | None = None,
) -> JSONResponse:
    """Download and prepare Sigma reference documents."""
    # For now, we use default paths for sigma ref
    rules_dir = os.environ.get("SIGMA_RULES_DIR", "data/sigma_rules")
    output_dir = "data/sigma_ref_docs"

    try:
        db = DatabaseService.get_instance()
        summary = download_references(
            rules_dir=rules_dir, output_dir=output_dir, db=db, supported_types={"markdown"}
        )
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to index sigma ref: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
