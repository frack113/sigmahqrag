"""Global service manager for subprocesses."""

from __future__ import annotations

from pathlib import Path

_subprocess_manager = None


def get_subprocess_manager():
    """Get or create the global subprocess manager."""
    global _subprocess_manager
    if _subprocess_manager is None:
        from src.shared.subprocess_manager import SubprocessManager

        _subprocess_manager = SubprocessManager(
            logs_dir=Path("data/logs"),
            pid_dir=Path("data/pids"),
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
