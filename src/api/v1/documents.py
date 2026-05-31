"""Documents API v1."""

from __future__ import annotations

import logging
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.back.database.service import DatabaseService
from src.back.documents.models import (
    IngestRequest,
    IngestResult,
)
from src.back.documents.sigma_ref_downloader import download_references
from src.back.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES
from src.back.documents.parser import scan_directory
from src.back.rag.ingestion import IngestionPipelineBuilder
from src.back.rag.transforms import TransformRegistry
from src.shared.config import get_config

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


def _ingest_with_pipeline(
    file_paths: list[str],
    mode: str,
) -> tuple[list[IngestResult], int]:
    """Ingest files using IngestionPipelineBuilder with per-file result tracking.

    Args:
        file_paths: List of file paths to ingest.
        mode: 'flat' or 'rich' chunking mode.

    Returns:
        Tuple of (results list, total chunks indexed).
    """
    from src.back.rag.transforms.base import TransformConfig
    from src.back.rag.ingestion import SOURCE_CHUNK_CONFIG

    collection_name = "sigma_rules"
    builder = IngestionPipelineBuilder(collection_name=collection_name)

    # Collect documents for transformable files
    all_documents: list = []
    file_doc_counts: dict[str, int] = {}
    results: list[IngestResult] = []

    for file_path in file_paths:
        transform_cls = TransformRegistry.find_for_file(file_path)
        if transform_cls is None:
            results.append(
                IngestResult(
                    file=file_path,
                    success=False,
                    error="No suitable transform found",
                )
            )
            continue

        try:
            source = "sigma_rules"
            chunk_cfg = SOURCE_CHUNK_CONFIG.get(source, {})
            transform_config = TransformConfig(
                collection_name=collection_name,
                model_name=builder._model_name,
                chunk_size=chunk_cfg.get("chunk_size", 512),
                chunk_overlap=chunk_cfg.get("chunk_overlap", 50),
                enable_rich_chunks=(mode == "rich"),
            )
            transform_instance = transform_cls(config=transform_config)
            docs = transform_instance.run(Path(file_path))
            file_doc_counts[file_path] = len(docs)
            all_documents.extend(docs)
            results.append(
                IngestResult(
                    file=file_path,
                    success=True,
                    chunks=len(docs),
                )
            )
        except Exception:
            logger.exception("Transform failed for %s", file_path)
            results.append(
                IngestResult(
                    file=file_path,
                    success=False,
                    error="Transform failed",
                )
            )

    # Run the embedding pipeline on all collected documents
    total_chunks = 0
    if all_documents:
        nodes = builder.run(all_documents)
        total_chunks = len(nodes) if nodes else 0

    return results, total_chunks


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
    mode = request.mode if request and request.mode else "flat"
    directory = request.directory if request else None
    recursive = request.recursive if request and request.recursive is not None else True

    if directory:
        directories = [directory]
    else:
        cfg = get_config()
        directories = [cfg.paths_github_dir, cfg.local_documents_path]

    all_files: list[str] = []
    for d in directories:
        files = scan_directory(d, recursive=recursive)
        logger.info("Found %d files in %s", len(files), d)
        all_files.extend(files)

    files = sorted(all_files)
    logger.info("Found %d files total", len(files))

    results, total_chunks = _ingest_with_pipeline(files, mode)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return JSONResponse(
        content={
            "success": True,
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "indexed_chunks": total_chunks,
            "mode": mode,
            "results": [r.model_dump() for r in results],
        }
    )


@router.post("/index-sigma-ref")
async def index_sigma_ref(
    request: IngestRequest | None = None,
) -> JSONResponse:
    """Download and prepare Sigma reference documents."""
    cfg = get_config()
    rules_dir = cfg.paths_sigma_rules_dir
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
        logger.error("Failed to index sigma ref: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500, content={"success": False, "error": "An internal error occurred"}
        )
