"""Global service manager for subprocesses."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.subprocess_manager import SubprocessManager

_subprocess_manager: SubprocessManager | None = None


def get_subprocess_manager() -> SubprocessManager:
    """Get or create the global subprocess manager."""
    global _subprocess_manager
    if _subprocess_manager is None:
        from pathlib import Path

        from src.config.settings import get_config
        from src.shared.subprocess_manager import SubprocessManager

        config = get_config()
        _subprocess_manager = SubprocessManager(
            logs_dir=Path(config.paths_logs_dir).resolve(),
            pid_dir=Path(config.paths_logs_dir.replace("logs", "pids")).resolve(),
        )
    return _subprocess_manager


async def shutdown_all_services() -> None:
    """Shutdown all subprocess services on app exit."""
    try:
        manager = get_subprocess_manager()
        await manager.stop_all()
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Error shutting down services: {e}")
