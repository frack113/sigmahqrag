"""Llama.cpp auto-start on application launch."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from src.shared.exceptions import ServiceStartError

logger = logging.getLogger(__name__)

_llamacpp_started_by_us: bool = False
_started_binary_service = None


def is_llamacpp_running() -> bool:
    """Return whether llama.cpp is running (HTTP health check)."""
    import httpx
    from urllib.parse import urlparse

    try:
        from src.config.settings import get_config

        config = get_config()
        base_url = config.llama_base_url or "http://127.0.0.1:8080"
        port = urlparse(base_url).port or 8080
        response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def _find_first_model() -> str | None:
    """Find the first available GGUF model in the LLM directory.

    Filters out ``mmproj-*.gguf`` files (multimodal projection layers) since
    those are not standalone models.
    """
    from src.config.settings import LLM_DIR

    gguf_files = sorted(
        f for f in Path(LLM_DIR).rglob("*.gguf") if not f.name.startswith("mmproj-")
    )
    if not gguf_files:
        logger.warning("No GGUF models found in %s", LLM_DIR)
        return None
    logger.info("Auto-selected model: %s", gguf_files[0])
    return str(gguf_files[0])


async def start_llamacpp() -> None:
    from src.config.settings import get_config

    config = get_config()

    if not config.service_is_autostart("llama"):
        logger.info("llama.cpp auto-start disabled (not internal or autorun=false) -- skipping")
        return

    from urllib.parse import urlparse

    llama_port = urlparse(config.llama_base_url).port or 8080

    from src.infrastructure.llm.llamacpp.health import check_health

    try:
        health = await check_health(timeout=2.0, port=llama_port)
        if health.get("status") == "active":
            logger.info("llama.cpp is already running -- skipping auto-start")
            return
    except Exception:
        logger.warning("llama.cpp health check failed -- will attempt start")

    llama_bin = Path(config.llama_binary_path).resolve()
    if sys.platform == "win32":
        candidates = ("llama-server.exe", "llama-server")
    else:
        candidates = ("llama-server", "llama-server.exe")
    llama_exe: Path | None = None
    for name in candidates:
        candidate = llama_bin / name
        if candidate.exists():
            llama_exe = candidate
            break

    if llama_exe is None:
        logger.warning("llama.cpp binary not found at %s -- skipping auto-start", llama_bin)
        return

    model_path = _find_first_model()
    if not model_path:
        raise ServiceStartError("No LLM model configured or found -- cannot start llama.cpp")

    from src.infrastructure.llm.llamacpp.service import LlamaBinaryService

    global _started_binary_service
    service = LlamaBinaryService()

    try:
        result = await service.start(model_path=model_path, port=llama_port)
        if not result.get("success"):
            raise ServiceStartError(f"Failed to start llama.cpp: {result.get('error')}")
    except ServiceStartError:
        raise
    except Exception as e:
        raise ServiceStartError(f"llama.cpp start raised an exception: {e}") from e

    _started_binary_service = service

    for _ in range(10):
        try:
            health = await check_health(timeout=2.0, port=llama_port)
            if health.get("status") == "active":
                global _llamacpp_started_by_us
                _llamacpp_started_by_us = True
                logger.info("llama.cpp started successfully and healthy")
                return
        except Exception:
            pass
        await asyncio.sleep(1)

    _llamacpp_started_by_us = True
    raise ServiceStartError("llama.cpp process started but health check timed out after 10s")


async def stop_llamacpp() -> None:
    global _llamacpp_started_by_us
    if not _llamacpp_started_by_us:
        return

    try:
        if _started_binary_service is not None:
            result = await _started_binary_service.stop()
        else:
            from src.infrastructure.llm.llamacpp.service import LlamaBinaryService

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
