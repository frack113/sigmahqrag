from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

import jinja2
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
        from src.back import get_qdrant_version

        version = get_qdrant_version()

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

    # Configuration for Qdrant connection
    from src.shared import get_qdrant_config

    config = get_qdrant_config()
    host = config.get("host", "127.0.0.1")
    try:
        port = int(config.get("port", 6333))
    except (ValueError, TypeError):
        port = 6333

    try:
        if action == "download_update":
            manager = create_download_manager()

            async def post_install_call(target_path: Path):
                template_path = Path("templates/config.yaml.j2")
                if not template_path.exists():
                    logger.error(f"Template not found: {template_path}")
                    return

                try:
                    template = jinja2.Template(template_path.read_text())

                    from src.shared import QDRANT_STORAGE_DIR

                    storage_path = QDRANT_STORAGE_DIR.resolve().as_posix()
                    snapshots_path = (QDRANT_STORAGE_DIR / "snapshots").resolve().as_posix()

                    rendered = template.render(
                        storage_path=storage_path,
                        snapshots_path=snapshots_path
                    )

                    config_dir = target_path / "config"
                    config_dir.mkdir(parents=True, exist_ok=True)
                    config_file = config_dir / "api/v1/qdrant/config.yaml"
                    # Wait, I should check where the config file should be written.
                    # Looking at the original code:
                    # config_file = config_dir / "config.yaml"
                    # Let me fix that.
                    config_file = config_dir / "config.yaml"
                    config_file.write_text(rendered)
                    logger.info(f"Qdrant config generated at: {config_file}")
                except Exception as e:
                    logger.error(f"Failed to generate Qdrant config: {e}")

            download_id = await manager.start_download(
                service="qdrant",
                version=payload.version,
                post_install_callback=post_install_call
            )

            return QdrantActionResponse(
                status="success",
                action=action,
                data={"download_id": download_id},
                message=f"Download initiated for version {payload.version}",
            )

        elif action == "service_control":
            service_manager = create_qradant_service() # Wait, typo in service name?
            # Let me check the original code:
            # service_manager = create_qdrant_service()
            # I'll use the correct one.
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
                v_size = (
                    payload.config.get("vector_size", 384) if payload.config else 384
                )
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
                    status="success", action=action, message="Data deleted",
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
