"""File Discovery and Embedding API v1."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile
from pydantic import BaseModel

from src.api.dependencies import get_dispatcher
from src.back.database.service import DatabaseService
from src.shared.config import get_config
from src.worker.enums import WorkerName
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP, identify
from src.shared.utils import iso_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["v1-files"])


class FileOperationResponse(BaseModel):
    """Response for file operations."""

    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None


class LocalFileAddResponse(BaseModel):
    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None


class LocalFileDeleteResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None


class LocalFileListResponse(BaseModel):
    success: bool
    data: list[dict[str, Any]] | None = None
    total: int = 0
    message: str | None = None
    error: str | None = None


@router.post("/list", response_model=FileOperationResponse)
async def file_list(
    dispatcher=Depends(get_dispatcher),
) -> FileOperationResponse:
    """Trigger file discovery across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if dispatcher.ask_for_worker(
        WorkerName.GITHUB_DISCOVERY,
        task_type=WorkerName.GITHUB_DISCOVERY.value,
        collection_name="all",
    ):
        triggered.append(WorkerName.GITHUB_DISCOVERY.value)
    else:
        busy.append(WorkerName.GITHUB_DISCOVERY.value)

    if dispatcher.ask_for_worker(
        WorkerName.LOCAL_DISCOVERY,
        task_type=WorkerName.LOCAL_DISCOVERY.value,
        collection_name="local",
    ):
        triggered.append(WorkerName.LOCAL_DISCOVERY.value)
    else:
        busy.append(WorkerName.LOCAL_DISCOVERY.value)

    if dispatcher.ask_for_worker(
        WorkerName.SIGMAREF_DISCOVERY,
        task_type=WorkerName.SIGMAREF_DISCOVERY.value,
        collection_name="sigmaref",
    ):
        triggered.append(WorkerName.SIGMAREF_DISCOVERY.value)
    else:
        busy.append(WorkerName.SIGMAREF_DISCOVERY.value)

    if busy:
        return FileOperationResponse(
            success=False,
            error=f"Workers already busy: {', '.join(busy)}",
            data={"triggered": triggered} if triggered else None,
        )

    return FileOperationResponse(
        success=True,
        message=f"Discovery queued for: {', '.join(triggered)}",
        data={"tasks": triggered},
    )


@router.post("/embed", response_model=FileOperationResponse)
async def file_embed(
    dispatcher=Depends(get_dispatcher),
) -> FileOperationResponse:
    """Trigger file embedding across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if dispatcher.ask_for_worker(
        WorkerName.GITHUB_EMBEDDINGS,
        task_type=WorkerName.GITHUB_EMBEDDINGS.value,
        collection_name="all",
    ):
        triggered.append(WorkerName.GITHUB_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.GITHUB_EMBEDDINGS.value)

    if dispatcher.ask_for_worker(
        WorkerName.LOCAL_EMBEDDINGS,
        task_type=WorkerName.LOCAL_EMBEDDINGS.value,
        collection_name="local",
    ):
        triggered.append(WorkerName.LOCAL_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.LOCAL_EMBEDDINGS.value)

    if dispatcher.ask_for_worker(
        WorkerName.SIGMAREF_EMBEDDINGS,
        task_type=WorkerName.SIGMAREF_EMBEDDINGS.value,
        collection_name="sigmaref",
    ):
        triggered.append(WorkerName.SIGMAREF_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.SIGMAREF_EMBEDDINGS.value)

    if busy:
        return FileOperationResponse(
            success=False,
            error=f"Workers already busy: {', '.join(busy)}",
            data={"triggered": triggered} if triggered else None,
        )

    return FileOperationResponse(
        success=True,
        message=f"Embedding queued for: {', '.join(triggered)}",
        data={"tasks": triggered},
    )


@router.post("/local/add", response_model=LocalFileAddResponse)
async def add_local_file(
    file: UploadFile = FastAPIFile(...),
    collection_name: str = "local",
) -> LocalFileAddResponse:
    """Upload a local file to configured documents path.

    Args:
        file: The file to upload (supported types only).
        collection_name: The local collection name (default 'local').

    Returns:
        LocalFileAddResponse with success status and metadata.
    """
    cfg = get_config()
    base_path = Path(cfg.local_documents_path)
    base_path.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        return LocalFileAddResponse(success=False, error="No filename provided.")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_DOC_EXTENSION_MAP:
        return LocalFileAddResponse(
            success=False,
            error=f"Unsupported file type: {ext}",
            data={"supported_extensions": list(SUPPORTED_DOC_EXTENSION_MAP.keys())},
        )

    dest_path = base_path / file.filename
    if dest_path.exists():
        return LocalFileAddResponse(
            success=False,
            error=f"File already exists: {file.filename}",
        )

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        content_type = identify(dest_path).value
        file_bytes = dest_path.read_bytes()
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        file_size = dest_path.stat().st_size
    except Exception as e:
        logging.getLogger(__name__).error(f"Error reading file: {e}")
        content_type = ""
        content_hash = ""
        file_size = 0

    file_rel_path = dest_path.relative_to(base_path).as_posix()
    url_hash = hashlib.sha256(f"local/{collection_name}/{file_rel_path}".encode()).hexdigest()
    title = dest_path.stem

    db = DatabaseService.get_instance()
    db.upsert_doc_registry(
        {
            "url_hash": url_hash,
            "org": "local",
            "repo": collection_name,
            "content_type": content_type,
            "file_name": file_rel_path,
            "content_sha256": content_hash,
            "file_size": file_size,
            "original_url": f"file://{dest_path}",
            "normalized_url": f"file://{dest_path}",
            "rule_id": "00000000-0000-0000-0000-000000000000",
            "title": title,
            "timestamp": iso_now(),
            "last_seen": iso_now(),
            "embed_status": "discovery",
        }
    )

    return LocalFileAddResponse(
        success=True,
        message=f"File '{file.filename}' added successfully.",
        data={
            "url_hash": url_hash,
            "file_name": file_rel_path,
            "content_type": content_type,
            "file_size": file_size,
            "embed_status": "discovery",
        },
    )


@router.delete("/local/delete", response_model=LocalFileDeleteResponse)
async def delete_local_file(
    file_path: str,
) -> LocalFileDeleteResponse:
    """Delete a local file from configured documents path and doc_registry.

    Args:
        file_path: Absolute path to the file to delete.

    Returns:
        LocalFileDeleteResponse with success status.
    """
    fs_path = Path(file_path)

    if not fs_path.exists():
        return LocalFileDeleteResponse(success=False, error=f"File does not exist: {file_path}")

    try:
        fs_path.unlink()
    except OSError as e:
        logging.getLogger(__name__).error(f"Error deleting file from filesystem: {e}")
        return LocalFileDeleteResponse(success=False, error=f"Failed to delete file: {str(e)}")

    db = DatabaseService.get_instance()
    db.delete_doc_registry_by_url(file_path)

    return LocalFileDeleteResponse(
        success=True,
        message="File deleted successfully.",
    )


@router.get("/local/list", response_model=LocalFileListResponse)
async def list_local_files(
    limit: int = 1000,
    offset: int = 0,
) -> LocalFileListResponse:
    """List all local files from doc_registry.

    Args:
        limit: Maximum number of records to return (default 1000).
        offset: Number of records to skip for pagination (default 0).

    Returns:
        List of local file records with metadata and counts.
    """
    db = DatabaseService.get_instance()
    files = db.get_local_files(limit=limit, offset=offset)
    total = db.get_local_file_count()

    return LocalFileListResponse(
        success=True,
        data=files,
        total=total,
    )
