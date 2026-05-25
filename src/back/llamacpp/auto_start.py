"""Llama.cpp auto-start on application launch."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_llamacpp_started_by_us: bool = False
_started_binary_service = None


def _find_first_model() -> str | None:
    """Find the first available GGUF model in the LLM directory."""
    from src.shared import LLM_DIR

    gguf_files = sorted(Path(LLM_DIR).rglob("*.gguf"))
    if not gguf_files:
        logger.warning("No GGUF models found in %s", LLM_DIR)
        return None
    logger.info("Auto-selected model: %s", gguf_files[0])
    return str(gguf_files[0])


async def start_llamacpp() -> None:
    from src.shared import get_config

    config = get_config()

    if not config.llama_manage_internally:
        logger.info("llama.cpp manage_internally=false -- skipping auto-start")
        return

    from src.back.llamacpp.health import check_health

    try:
        health = await check_health(timeout=2.0, port=8080)
        if health.get("status") == "active":
            logger.info("llama.cpp is already running -- skipping auto-start")
            return
    except Exception:
        logger.warning("llama.cpp health check failed -- will attempt start")

    llama_bin = Path(config.llama_binary_path).resolve()
    llama_exe = llama_bin / "llama-server.exe"

    if not llama_exe.exists():
        logger.info("llama.cpp server binary not found at %s, will attempt download", llama_exe)
        try:
            from src.shared.download_manager import DownloadManager

            manager = DownloadManager()
            result = await asyncio.wait_for(
                manager.start_download(service="llama.cpp", version="latest"),
                timeout=120.0,
            )
            if not result.get("success"):
                logger.warning("Failed to download llama.cpp: %s", result.get("error"))
                return
        except TimeoutError:
            logger.warning("llama.cpp download timed out after 120s")
            return
        except Exception as e:
            logger.warning("llama.cpp download failed: %s", e)
            return

    model_path = config.llama_model_name or _find_first_model()
    if not model_path:
        logger.warning("No LLM model configured or found -- cannot start llama.cpp")
        return

    from src.back.llamacpp.service import LlamaBinaryService

    global _started_binary_service
    service = LlamaBinaryService()

    try:
        result = await service.start(model_path=model_path, port=8080)
        if not result.get("success"):
            logger.warning("Failed to start llama.cpp: %s", result.get("error"))
            return
    except Exception as e:
        logger.warning("llama.cpp start raised an exception: %s", e)
        return

    _started_binary_service = service

    for _ in range(10):
        try:
            health = await check_health(timeout=2.0, port=8080)
            if health.get("status") == "active":
                global _llamacpp_started_by_us
                _llamacpp_started_by_us = True
                logger.info("llama.cpp started successfully and healthy")
                return
        except Exception:
            pass
        await asyncio.sleep(1)

    _llamacpp_started_by_us = True
    logger.warning("llama.cpp process started but health check timed out after 10s")


async def stop_llamacpp() -> None:
    global _llamacpp_started_by_us
    if not _llamacpp_started_by_us:
        return

    try:
        if _started_binary_service is not None:
            result = await _started_binary_service.stop()
        else:
            from src.back.llamacpp.service import LlamaBinaryService

            service = LlamaBinaryService()
            result = await service.stop()

        if result.get("success"):
            logger.info("llama.cpp stopped (auto-started by app)")
        else:
            logger.warning("Failed to stop llama.cpp: %s", result.get("error"))
    except Exception as e:
        logger.warning("llama.cpp stop raised an exception: %s", e)
    finally:
        _llamacpp_started_by_us = False
