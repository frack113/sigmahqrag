"""Document ingestion API routes."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from src.api.dependencies import require_role
from src.auth.models import CurrentUser, UserRole
from src.documents.indexing import index_sigma_rules
from src.documents.models import (
    IngestRequest,
    IngestResponse,
    IngestResult,
)
from src.documents.parser import parse_sigma_rule, scan_directory
from src.documents.validator import validate_sigma_rule

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

security = HTTPBearer(auto_error=False)


def get_sigma_rules_dir() -> str:
    """Get Sigma rules directory from environment."""
    directory = os.environ.get("SIGMA_RULES_DIR")
    if not directory:
        raise ValueError("SIGMA_RULES_DIR environment variable not set")
    return directory


@router.post("/ingest", response_model=IngestResponse)
async def ingest_sigma_rules(
    request: IngestRequest | None = None,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
) -> IngestResponse:
    """Ingest Sigma rules from configured directory.

    Args:
        request: Optional IngestRequest with directory/recursive options
        current_user: Authenticated admin user

    Returns:
        IngestResponse with ingestion results
    """
    directory = request.directory if request else None
    recursive = request.recursive if request else True

    if not directory:
        directory = get_sigma_rules_dir()

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
                        error="; ".join(
                            f"{e.field}: {e.message}" for e in validation.errors
                        ),
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

    return IngestResponse(
        total_files=len(files),
        successful=len(successful_rules),
        failed=len(files) - len(successful_rules),
        results=results,
    )
