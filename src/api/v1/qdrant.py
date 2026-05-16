from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from src.back.qdrant import (
    check_health,
    create_collection,
    delete_collection,
    get_collection,
    list_collections,
)
from src.back.qdrant.service import create_qdrant_service
from src.back.qdrant.storage import delete_point, store_embeddings
from src.back.qdrant.storage import search as qdrant_search
from src.back.database.service import DatabaseService
from src.shared.download_manager import create_download_manager
from src.shared.schemas.qdrant import (
    QdrantActionRequest,
    QdrantActionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/qdrant", tags=["v1-qdrant"])

SERVICE_NAME = "qdrant"

# In-memory store for embed_sigmaref task progress
_embed_tasks: dict[str, dict] = {}
_embed_progress_queues: dict[str, asyncio.Queue] = {}


async def _embed_progress_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE progress updates for embed_sigmaref tasks."""
    queue = _embed_progress_queues.get(task_id)

    if not queue:
        yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
        return

    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"data: {json.dumps(data)}\n\n"

            if data.get("status") in ("completed", "failed"):
                break
        except TimeoutError:
            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
            break


async def _run_embed_sigmaref(
    task_id: str,
    registry_path: Path,
    collection_name: str,
    progress_queue: asyncio.Queue,
) -> None:
    """Background task to embed all files from the SigmaRef registry."""
    _embed_tasks[task_id]["status"] = "running"

    try:
        db = DatabaseService.get_instance()
        raw_entries = db.get_doc_registry()
        registry_entries = []
        for e in raw_entries:
            registry_entries.append(
                {
                    "hash": e.get("url_hash", ""),
                    "file_name": f"{e.get('url_hash', '')}.md",
                    "path": f"{e.get('url_hash', '')}.md",
                    **{k: v for k, v in e.items() if k not in ("url_hash",)},
                }
            )
        if not registry_entries:
            await progress_queue.put(
                {
                    "status": "completed",
                    "task_id": task_id,
                    "message": "No files found in registry",
                    "total": 0,
                    "processed": 0,
                }
            )
            _embed_tasks[task_id]["status"] = "completed"
            return

        total = len(registry_entries)
        _embed_tasks[task_id]["total"] = total
        _embed_tasks[task_id]["processed"] = 0
        await progress_queue.put(
            {
                "status": "processing",
                "task_id": task_id,
                "total": total,
                "processed": 0,
                "current_file": "",
            }
        )

        from llama_index.core.schema import Document

        from src.back.rag.ingestion import IngestionPipelineBuilder

        builder = IngestionPipelineBuilder(collection_name=collection_name)
        base_dir = registry_path

        for idx, entry in enumerate(registry_entries):
            file_hash = entry.get("hash", entry.get("id", ""))
            file_name = entry.get("file_name", "")
            relative_path = entry.get("path", entry.get("file_path", file_hash))
            file_path = (
                base_dir / file_hash
                if not (base_dir / relative_path).exists()
                else base_dir / relative_path
            )

            _embed_tasks[task_id]["processed"] = idx
            _embed_tasks[task_id]["current_file"] = file_name or file_hash
            await progress_queue.put(
                {
                    "status": "processing",
                    "task_id": task_id,
                    "total": total,
                    "processed": idx,
                    "current_file": file_name or file_hash,
                }
            )

            # Read the document
            doc_text = ""
            try:
                doc_text = file_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                logger.warning(f"File not found: {file_path}, skipping")
                _embed_tasks[task_id].setdefault("skipped", []).append(file_name or file_hash)
                continue
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                _embed_tasks[task_id].setdefault("errors", []).append(
                    {"file": file_name or file_hash, "error": str(e)}
                )
                continue

            # Create metadata from registry entry
            metadata = dict(entry)
            metadata.pop("hash", None)
            metadata["source"] = "sigmaref"
            metadata["collection"] = collection_name

            doc = Document(text=doc_text, metadata=metadata)
            try:
                builder.run(documents=[doc])
            except Exception as e:
                logger.error(f"Error embedding {file_name or file_hash}: {e}")
                _embed_tasks[task_id].setdefault("errors", []).append(
                    {"file": file_name or file_hash, "error": str(e)}
                )

            # Small yield to prevent blocking
            await asyncio.sleep(0)

        processed = (
            len(registry_entries)
            - len(_embed_tasks[task_id].get("errors", []))
            - len(_embed_tasks[task_id].get("skipped", []))
        )
        _embed_tasks[task_id]["status"] = "completed"
        _embed_tasks[task_id]["processed"] = processed
        _embed_tasks[task_id]["total"] = total
        await progress_queue.put(
            {
                "status": "completed",
                "task_id": task_id,
                "total": total,
                "processed": processed,
                "errors": len(_embed_tasks[task_id].get("errors", [])),
                "skipped": len(_embed_tasks[task_id].get("skipped", [])),
                "message": f"Processed {processed}/{total} files",
            }
        )

    except Exception as e:
        logger.error(f"Embed SigmaRef task {task_id} failed: {e}")
        _embed_tasks[task_id]["status"] = "failed"
        await progress_queue.put(
            {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
            }
        )
    finally:
        # Clean up after a delay
        async def _cleanup():
            await asyncio.sleep(300)
            _embed_tasks.pop(task_id, None)
            _embed_progress_queues.pop(task_id, None)

        asyncio.create_task(_cleanup())


async def _progress_generator(download_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE progress updates."""
    manager = create_download_manager()
    queue = manager.get_progress_stream(download_id)

    if not queue:
        yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
        return

    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"data: {json.dumps(data)}\n\n"

            if data.get("status") in ("completed", "cancelled", "failed"):
                break
        except TimeoutError:
            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
            break


@router.get("/status")
async def qdrant_status():
    """Get status and version for qdrant service."""
    try:
        health_result = await check_health()
        from src.shared import get_config

        config = get_config()
        version = config.qdrant_version
        is_healthy = health_result.get("status") == "active"

        manager = create_download_manager()
        downloads = {
            k: {"status": v.status, "service": v.service, "version": v.version}
            for k, v in manager.active_downloads.items()
            if v.service == SERVICE_NAME
        }

        return JSONResponse(
            content={
                "service": SERVICE_NAME,
                "healthy": is_healthy,
                "current_version": version or "unknown",
                "downloads": downloads,
                "mode": config.qdrant_mode,
            }
        )
    except Exception as e:
        logger.error(f"Qdrant status error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/progress/{download_id}")
async def qdrant_progress(download_id: str):
    """Stream progress for a specific qdrant download."""
    try:
        return StreamingResponse(
            _progress_generator(download_id),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"qdrant progress error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/embed/{task_id}")
async def embed_progress(task_id: str):
    """Get the status of an embed_sigmaref task."""
    task = _embed_tasks.get(task_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"status": "not_found", "message": "Task not found"},
        )
    return JSONResponse(
        content={
            "status": task.get("status", "unknown"),
            "task_id": task_id,
            "details": task,
        }
    )


@router.get("/embed/{task_id}/stream")
async def embed_progress_stream(task_id: str):
    """Stream SSE progress for an embed_sigmaref task."""
    try:
        return StreamingResponse(
            _embed_progress_generator(task_id),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"embed progress error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("")
async def qdrant_action(request: QdrantActionRequest) -> QdrantActionResponse:
    """Unified endpoint for all Qdrant actions."""
    action = request.action
    payload = request.payload

    from src.shared import get_config

    config = get_config()
    host = config.qdrant_host
    port = config.qdrant_port

    try:
        if action == "download_update":
            manager = create_download_manager()

            async def post_install_call(target_path: Path):
                logger.info(f"post_install_call triggered: {target_path}")
                try:
                    from src.shared.config import Config

                    Config.ensure_qdrant_config()
                    logger.info("Qdrant config generated via Config.ensure_qdrant_config()")
                except Exception as e:
                    import traceback

                    logger.error(f"Failed to generate Qdrant config: {e}")
                    logger.error(traceback.format_exc())

            download_id = await manager.start_download(
                service="qdrant",
                version=payload.version,
                post_install_callback=post_install_call,
            )

            return QdrantActionResponse(
                status="success",
                action=action,
                data={"download_id": download_id},
                message=f"Download initiated for version {payload.version}",
            )

        elif action == "service_control":
            service_manager = create_qdrant_service()
            command = payload.command
            if command == "start":
                from src.shared import QDRANT_STORAGE_DIR

                result = await service_manager.start(storage_path=str(QDRANT_STORAGE_DIR))
            elif command == "stop":
                result = await service_manager.stop()
            elif command == "restart":
                await service_manager.stop()
                result = await service_manager.start()
            else:
                raise ValueError(f"Unknown command: {command}")
            return QdrantActionResponse(status="success", action=action, data=result)

        elif action == "progress":
            return JSONResponse(
                status_code=307,
                headers={"Location": f"/api/v1/qdrant/progress/{payload.download_id}"},
            )

        elif action == "cancel":
            manager = create_download_manager()
            manager.cancel_download(payload.download_id)
            return QdrantActionResponse(
                status="success",
                action=action,
                message=f"Download {payload.download_id} cancelled",
            )

        elif action == "collection_management":
            op = payload.operation
            name = payload.collection_name
            if op == "list":
                data = await list_collections(host, port)
                return QdrantActionResponse(status="success", action=action, data=data)
            elif op == "create":
                v_size = payload.config.vector_size if payload.config else 384
                await create_collection(host, port, name, v_size)
                return QdrantActionResponse(
                    status="success",
                    action=action,
                    message=f"Collection {name} created",
                )
            elif op == "delete":
                await delete_collection(host, port, name)
                return QdrantActionResponse(
                    status="success",
                    action=action,
                    message=f"Collection {name} deleted",
                )
            elif op == "get":
                data = await get_collection(host, port, name)
                return QdrantActionResponse(status="success", action=action, data=data)
            else:
                raise ValueError(f"Unknown operation: {op}")

        elif action == "data_management":
            op = payload.operation
            name = payload.collection_name
            if op == "add" or op == "update":
                if not payload.vector or not payload.id:
                    raise ValueError("id and vector are required for add/update")
                success = await store_embeddings(
                    embeddings=[payload.vector],
                    documents=["placeholder"],
                    metadata=[payload.payload or {}],
                    collection_name=name,
                )
                if not success:
                    raise ValueError("Failed to add/update data")
                return QdrantActionResponse(
                    status="success", action=action, message="Data processed"
                )
            elif op == "delete":
                if not payload.id:
                    raise ValueError("id is required for delete")
                success = await delete_point(name, payload.id, host, port)
                if not success:
                    raise ValueError("Failed to delete data")
                return QdrantActionResponse(
                    status="success",
                    action=action,
                    message="Data deleted",
                )
            else:
                raise ValueError(f"Unknown operation: {op}")

        elif action == "vector_search":
            results = await qdrant_search(
                query_embedding=payload.query_vector,
                collection_name=payload.collection_name,
                top_k=payload.top_k,
            )
            return QdrantActionResponse(status="success", action=action, data=results)

        elif action == "embed_sigmaref":
            registry_path = Path(payload.registry_path)

            # Check if a task is already running
            existing_running = [
                tid for tid, t in _embed_tasks.items() if t.get("status") in ("running", "pending")
            ]
            if existing_running:
                return QdrantActionResponse(
                    status="error",
                    action=action,
                    error_code="ALREADY_RUNNING",
                    message="Task already in progress",
                )

            # Check Qdrant health
            try:
                from src.back.qdrant import check_health as qdrant_health

                if not await qdrant_health():
                    return QdrantActionResponse(
                        status="error",
                        action=action,
                        error_code="QDRANT_DOWN",
                        message="Qdrant is unreachable",
                    )
            except Exception:
                return QdrantActionResponse(
                    status="error",
                    action=action,
                    error_code="QDRANT_DOWN",
                    message="Qdrant is unreachable",
                )

            task_id = str(uuid.uuid4())
            progress_queue = asyncio.Queue()
            _embed_tasks[task_id] = {
                "id": task_id,
                "status": "pending",
                "action": action,
                "collection_name": payload.collection_name,
                "registry_path": str(payload.registry_path),
            }
            _embed_progress_queues[task_id] = progress_queue

            # Launch the background task
            asyncio.create_task(
                _run_embed_sigmaref(
                    task_id=task_id,
                    registry_path=registry_path,
                    collection_name=payload.collection_name,
                    progress_queue=progress_queue,
                )
            )

            return QdrantActionResponse(
                status="success",
                action=action,
                data={"task_id": task_id},
                message="SigmaRef embedding started",
            )

        else:
            return QdrantActionResponse(
                status="error",
                action=action,
                error_code="UNKNOWN_ACTION",
                message=f"Action {action} not supported",
            )

    except Exception as e:
        logger.error(f"Qdrant action error ({action}): {e}")
        return QdrantActionResponse(
            status="error", action=action, error_code="ACTION_FAILED", message=str(e)
        )
