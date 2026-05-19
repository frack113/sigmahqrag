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


async def _embed_progress_generator(worker_type: str) -> AsyncGenerator[str, None]:
    """Generate SSE progress updates by polling the database."""
    db = DatabaseService.get_instance()
    while True:
        try:
            status_data = db.get_worker_progress(worker_type)
            if not status_data:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break

            yield f"data: {json.dumps(status_data)}\n\n"

            if status_data.get("status") in ("completed", "failed", "idle"):
                break
        except Exception as e:
            logger.error(f"SSE error for {worker_type}: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
            break

        await asyncio.sleep(2)


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


@router.get("/embed/{worker_type}")
async def embed_progress(worker_type: str):
    """Get the status of an embedding worker."""
    db = DatabaseService.get_instance()
    status_data = db.get_worker_progress(worker_type)
    if not status_data:
        return JSONResponse(
            status_code=404,
            content={"status": "not_found", "message": "Worker not found"},
        )
    return JSONResponse(
        content={
            "status": status_data.get("status", "unknown"),
            "worker_type": worker_type,
            "details": status_data,
        }
    )


@router.get("/embed/{worker_type}/stream")
async def embed_progress_stream(worker_type: str):
    """Stream SSE progress for an embedding worker."""
    try:
        return StreamingResponse(
            _embed_progress_generator(worker_type),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"embed progress error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/embed-status/{worker_type}")
async def worker_embed_status(worker_type: str):
    """Get embedding progress for a worker type."""
    db = DatabaseService.get_instance()
    progress = db.get_worker_progress(worker_type)
    if not progress:
        return JSONResponse(
            status_code=404,
            content={"status": "not_found", "message": "Worker not found"},
        )
    return JSONResponse(content=progress)


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
                logger.info(f"post_intall_call triggered: {target_path}")
                try:
                    from src.shared.config import Config

                    Config.ensure_qdrant_config()
                    logger.info("Qdrant config generated via Config.ensure_qdrant_config()")
                except Exception as e:
                    logger.error(f"Failed to generate Qdrant config: {e}")

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
                v_size = payload.config.get("vector_size", 384) if payload.config else 384
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
            db = DatabaseService.get_instance()

            if db.is_worker_busy("sigmaref_embeddings"):
                return QdrantActionResponse(
                    status="error",
                    action=action,
                    error_code="ALREADY_RUNNING",
                    message="Task already in progress",
                )

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
            task = {
                "task_id": task_id,
                "task_type": "sigmaref_embeddings",
                "collection_name": payload.collection_name,
            }

            db.upsert_worker_state(
                worker_type="sigmaref_embeddings",
                status="running",
                current_task_id=task_id,
            )

            # Trigger via dispatcher if available, otherwise use background task
            from src.main import app

            if app and hasattr(app, "state") and hasattr(app.state, "dispatcher"):
                await app.state.dispatcher.queue_task("sigmaref_embeddings", task)
            else:
                # Fallback for direct calls or tests
                import asyncio
                from src.back.worker.workers.sigmaref_embedding_worker import (
                    SigmaRefEmbeddingWorker,
                )

                asyncio.create_task(SigmaRefEmbeddingWorker(db).process(task))

            return QdrantActionResponse(
                status="success",
                action=action,
                data={"task_id": task_id},
                message="SigmaRef embedding queued (will start within 5s)",
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
            status="error",
            action=action,
            error_code="ACTION_FAILED",
            message=str(e),
        )
