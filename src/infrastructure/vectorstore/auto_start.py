"""Qdrant auto-start on application launch."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_qdrant_started_by_us: bool = False
_started_binary_service: Any = None


async def start_qdrant(
    installer_service: Any | None = None,
    binary_service: Any | None = None,
    health_check: Callable[..., Awaitable[dict]] | None = None,
) -> None:
    from src.config.settings import get_config

    config = get_config()

    if not config.service_is_autostart("qdrant"):
        logger.info("Qdrant auto-start disabled (not internal or autorun=false) -- skipping")
        return

    if health_check is None:
        from src.infrastructure.vectorstore.health import check_health as health_check

    assert health_check is not None
    try:
        health = await health_check(timeout=2.0, port=config.qdrant_port)
        if health.get("status") == "active":
            logger.info("Qdrant is already running -- skipping auto-start")
            return
    except Exception:
        logger.warning("Qdrant health check failed -- will attempt start anyway")

    qdrant_bin = Path(config.qdrant_binary_path).resolve()
    if sys.platform == "win32":
        qdrant_candidates = ("qdrant.exe", "qdrant")
    else:
        qdrant_candidates = ("qdrant", "qdrant.exe")
    qdrant_exe: Path | None = None
    for name in qdrant_candidates:
        candidate = qdrant_bin / name
        if candidate.exists():
            qdrant_exe = candidate
            break

    if qdrant_exe is None:
        logger.info("Qdrant binary not found, downloading...")
        if installer_service is None:
            from src.infrastructure.vectorstore.downloader import QdrantInstallerService

            installer_service = QdrantInstallerService()
        try:
            result = await asyncio.wait_for(installer_service.download_binary(), timeout=120.0)
            if not result.get("success"):
                logger.warning(f"Failed to download Qdrant: {result.get('error')}")
                return
        except TimeoutError:
            logger.warning("Qdrant download timed out after 120s")
            return
        except Exception as e:
            logger.warning(f"Qdrant download failed: {e}")
            return

    if binary_service is None:
        from src.infrastructure.vectorstore.service import QdrantBinaryService

        binary_service = QdrantBinaryService()

    try:
        result = await binary_service.start()
        if not result.get("success"):
            logger.warning(f"Failed to start Qdrant: {result.get('error')}")
            return
    except Exception as e:
        logger.warning(f"Qdrant start raised an exception: {e}")
        return

    global _qdrant_started_by_us, _started_binary_service
    _started_binary_service = binary_service

    assert health_check is not None
    for _ in range(10):
        try:
            health = await health_check(timeout=2.0, port=config.qdrant_port)
            if health.get("status") == "active":
                _qdrant_started_by_us = True
                logger.info("Qdrant started successfully and healthy")
                return
        except Exception:
            pass
        await asyncio.sleep(1)

    _qdrant_started_by_us = True
    logger.warning("Qdrant process started but health check timed out after 10s")


async def stop_qdrant() -> None:
    global _qdrant_started_by_us
    if not _qdrant_started_by_us:
        return

    try:
        if _started_binary_service is not None:
            result = await _started_binary_service.stop()
        else:
            from src.infrastructure.vectorstore.service import QdrantBinaryService

            service = QdrantBinaryService()
            result = await service.stop()

        if result.get("success"):
            logger.info("Qdrant stopped (auto-started by app)")
        else:
            logger.warning(f"Failed to stop Qdrant: {result.get('error')}")
    except Exception as e:
        logger.warning(f"Qdrant stop raised an exception: {e}")
    finally:
        _qdrant_started_by_us = False
