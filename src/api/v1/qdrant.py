from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.sse import download_progress_generator
from src.back.database.service import DatabaseService
from src.back.qdrant.collections import (
    list_collections,
    create_collection,
    delete_collection,
    get_collection,
)
from src.back.qdrant.health import check_health
from src.back.qdrant.service import get_qdrant_service
from src.back.qdrant.storage import store_embeddings, delete_point, search as qdrant_search
from src.shared.download_manager import create_download_manager
from src.shared.schemas.qdrant import (
    CancelPayload,
    CollectionManagementPayload,
    DataManagementPayload,
    DownloadUpdatePayload,
    ProgressPayload,
    QdrantActionRequest,
    QdrantActionResponse,
    ServiceControlPayload,
    VectorSearchPayload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/qdrant", tags=["v1-qdrant"])

SERVICE_NAME = "qdrant"


@router.get("/status")
async def qdrant_status():
    """Get status and version for qdrant service."""
    try:
        health_result = await check_health()
        from src.shared import get_config

        config = get_config()
        qdrant_base_url = config.qdrant_base_url
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
                "mode": "managed" if config.qdrant_manage_internally else "external",
                "base_url": qdrant_base_url,
            }
        )
    except Exception as e:
        logger.error(f"Qdrant status error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/progress/{download_id}")
async def qdrant_progress(download_id: str):
    """Stream progress for a specific qdrant download."""
    try:
        return StreamingResponse(
            download_progress_generator(download_id),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"qdrant progress error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.post("", response_model=None)
async def qdrant_action(
    request: QdrantActionRequest, req: Request
) -> QdrantActionResponse | JSONResponse:
    """Unified endpoint for all Qdrant actions."""
    action = request.action
    payload = request.payload

    from src.shared import get_config

    config = get_config()
    host = config.qdrant_host
    port = config.qdrant_port

    try:
        if isinstance(payload, DownloadUpdatePayload):
            manager = create_download_manager()

            async def post_install_call(target_path: Path):
                logger.info(f"post_intall_call triggered: {target_path}")
                try:
                    from src.shared import Config

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

        elif isinstance(payload, ServiceControlPayload):
            service_manager = get_qdrant_service()
            command = payload.command
            if command == "start":
                result = await service_manager.start()
            elif command == "stop":
                result = await service_manager.stop()
            elif command == "restart":
                await service_manager.stop()
                result = await service_manager.start()
            else:
                raise ValueError(f"Unknown command: {command}")
            return QdrantActionResponse(status="success", action=action, data=result)

        elif isinstance(payload, ProgressPayload):
            return JSONResponse(
                content=None,
                status_code=307,
                headers={"Location": f"/api/v1/qdrant/progress/{payload.download_id}"},
            )

        elif isinstance(payload, CancelPayload):
            manager = create_download_manager()
            await manager.cancel_download(payload.download_id)
            return QdrantActionResponse(
                status="success",
                action=action,
                message=f"Download {payload.download_id} cancelled",
            )

        elif isinstance(payload, CollectionManagementPayload):
            op = payload.operation
            if op == "list":
                data = await list_collections(host, port)
                return QdrantActionResponse(status="success", action=action, data=data)
            name = payload.collection_name
            if op not in ("create", "delete", "get"):
                raise ValueError(f"Unknown operation: {op}")
            if name is None:
                raise ValueError(f"collection_name is required for operation '{op}'")
            if op == "create":
                v_size = payload.config.get("vector_size", 384) if payload.config else 384
                await create_collection(host, port, name, v_size)
                return QdrantActionResponse(
                    status="success",
                    action=action,
                    message=f"Collection {name} created",
                )
            elif op == "delete":
                await delete_collection(host, port, name)
                db = DatabaseService.get_instance()
                db.reset_embed_status_for_collection(name)
                return QdrantActionResponse(
                    status="success",
                    action=action,
                    message=f"Collection {name} deleted, embed status reset to discovery",
                )
            elif op == "get":
                col_data = await get_collection(host, port, name)
                return QdrantActionResponse(status="success", action=action, data=col_data)

        elif isinstance(payload, DataManagementPayload):
            dm_op = payload.operation
            name = payload.collection_name
            if dm_op == "add" or dm_op == "update":
                if not payload.vector or not payload.id:
                    raise ValueError("id and vector are required for add/update")
                assert isinstance(name, str)
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
            elif dm_op == "delete":
                if not payload.id:
                    raise ValueError("id is required for delete")
                assert isinstance(name, str)
                success = await delete_point(name, payload.id, host, port)
                if not success:
                    raise ValueError("Failed to delete data")
                return QdrantActionResponse(
                    status="success",
                    action=action,
                    message="Data deleted",
                )
            else:
                raise ValueError(f"Unknown operation: {dm_op}")

        elif isinstance(payload, VectorSearchPayload):
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
        logger.error(
            "Qdrant action error (%s): %s: %s",
            action,
            type(e).__name__,
            e,
            exc_info=True,
        )
        return QdrantActionResponse(
            status="error",
            action=action,
            error_code="ACTION_FAILED",
            message="An internal error occurred",
        )
