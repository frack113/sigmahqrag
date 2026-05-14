from __future__ import annotations

import asyncio
import json
import logging
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
from src.shared.download_manager import create_download_manager
from src.shared.schemas import QdrantActionRequest, QdrantActionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/qdrant", tags=["v1-qdrant"])

SERVICE_NAME = "qdrant"


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
        is_healthy = await check_health()
        from src.shared import get_config

        config = get_config()
        version = config.qdrant_version

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
                    logger.info(
                        "Qdrant config generated via Config.ensure_qdrant_config()"
                    )
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

                result = await service_manager.start(
                    storage_path=str(QDRANT_STORAGE_DIR)
                )
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
