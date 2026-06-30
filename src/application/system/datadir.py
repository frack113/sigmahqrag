"""Central data directory lifecycle manager."""

from __future__ import annotations

import shutil
from enum import Enum
from pathlib import Path
from typing import NamedTuple


class HealthState(Enum):
    """Generic health state for any system component."""

    HEALTHY = "healthy"  # exists and operational
    DIRTY = "dirty"  # exists but degraded / unexpected content
    MISSING = "missing"  # does not exist or unavailable


class DirInfo(NamedTuple):
    relative: str
    absolute: Path


class DirStatus(NamedTuple):
    relative: str
    path: Path
    state: HealthState
    has_content: bool
    is_dirty: bool
    needs_creation: bool


class DataDirManager:
    """Manages the ``data/`` directory tree: official list, creation, cleanup, hard reset."""

    def __init__(self, base_dir: Path | str) -> None:
        self._base: Path = Path(base_dir).resolve()

    # ------------------------------------------------------------------
    # Official list
    # ------------------------------------------------------------------

    @property
    def base_dir(self) -> Path:
        return self._base

    @classmethod
    def official_dirs(cls, base: Path | str | None = None) -> list[DirInfo]:
        """Return the canonical list of data subdirectories.

        Derived from every ``data/`` path referenced in the application.
        """
        if base is None:
            base = "data"
        b = Path(base).resolve()
        # Flatten nested structures: only report the leaf dirs
        leaves: dict[str, Path] = {}
        for name in [
            "bin",
            "documents/local",
            "documents/sigmaref",
            "duckdb",
            "github",
            "models/llm",
            "models/embedding_e5",
            "models/embedding_fast",
            "qdrant_storage",
            "logs",
            "pids",
            "temp",
            "specification",
        ]:
            path = b / name
            leaves[name] = path
        # Top-level parents that are themselves official dirs
        for name in ["documents", "models", "duckdb", "qdrant_storage"]:
            path = b / name
            if name not in leaves:
                leaves[name] = path
        return [DirInfo(name, p) for name, p in leaves.items()]

    # ------------------------------------------------------------------
    # Creation / fix
    # ------------------------------------------------------------------

    def create_missing(self, dirs: list[DirInfo] | None = None) -> list[str]:
        """Create any official directories that do not yet exist.

        Returns the list of newly created directory paths (absolute).
        """
        if dirs is None:
            dirs = self.official_dirs(self._base)
        created: list[str] = []
        for d in dirs:
            if not d.absolute.exists():
                d.absolute.mkdir(parents=True, exist_ok=True)
                created.append(str(d.absolute))
        return created

    def ensure_all(self, dirs: list[DirInfo] | None = None) -> None:
        """Alias: create all official directories (idempotent)."""
        self.create_missing(dirs)

    # ------------------------------------------------------------------
    # Cleanup – remove non-official directories
    # ------------------------------------------------------------------

    def clean(self, dirs: list[DirInfo] | None = None) -> list[str]:
        """Remove directories under ``data/`` that are NOT in the official list.

        Returns the list of removed directory paths (absolute).
        """
        if dirs is None:
            dirs = self.official_dirs(self._base)
        official_names = {d.relative.split("/")[0] for d in dirs}
        # Handle nested names like "documents/local" → parent "documents" is already there
        parent_official: set[str] = set()
        for d in dirs:
            parts = d.relative.split("/")
            if len(parts) > 1:
                parent_official.add(parts[0])

        removed: list[str] = []
        if not self._base.exists():
            return removed
        for entry in self._base.iterdir():
            if not entry.is_dir():
                # Also consider stray files (e.g. a stray .sqlite) as trash
                try:
                    entry.unlink()
                    removed.append(str(entry))
                except OSError:
                    pass
                continue
            if entry.name not in official_names and entry.name not in parent_official:
                try:
                    shutil.rmtree(entry)
                    removed.append(str(entry))
                except OSError:
                    pass
        return removed

    # ------------------------------------------------------------------
    # Hard reset
    # ------------------------------------------------------------------

    def hard_reset(self, dirs: list[DirInfo] | None = None) -> dict[str, int]:
        """Delete the entire ``data/`` tree (if it exists), then recreate official structure.

        Returns ``{"removed": <n_removed>, "created": <n_created>}``.
        """
        removed_count = 0
        if self._base.exists():
            try:
                shutil.rmtree(self._base)
                removed_count = 1
            except OSError:
                pass

        new_dirs = self.official_dirs(self._base)
        created = self.create_missing(new_dirs)
        return {"removed": removed_count, "created": len(created)}

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @staticmethod
    def _inspect_dir(p: Path) -> DirStatus:
        """Inspect a single directory and return its full status."""
        exists = p.exists() and p.is_dir()
        if not exists:
            return DirStatus(
                relative="",
                path=p,
                state=HealthState.MISSING,
                has_content=False,
                is_dirty=False,
                needs_creation=True,
            )
        has_content = any(p.iterdir())
        is_dirty = False
        for entry in p.iterdir():
            if entry.name.startswith("."):
                is_dirty = True
                break
        state = HealthState.DIRTY if is_dirty else HealthState.HEALTHY
        return DirStatus(
            relative="",
            path=p,
            state=state,
            has_content=has_content,
            is_dirty=is_dirty,
            needs_creation=False,
        )

    def status(self, dirs: list[DirInfo] | None = None) -> dict[str, HealthState]:
        """Return a summary dict: ``{relative: healthy|dirty|missing}``."""
        if dirs is None:
            dirs = self.official_dirs(self._base)
        return {d.relative: self._inspect_dir(d.absolute).state for d in dirs}

    def status_detail(self, dirs: list[DirInfo] | None = None) -> list[DirStatus]:
        """Return full status for each directory with state, dirty, missing info."""
        if dirs is None:
            dirs = self.official_dirs(self._base)
        results = []
        for d in dirs:
            s = self._inspect_dir(d.absolute)
            results.append(
                DirStatus(
                    relative=d.relative,
                    path=s.path,
                    state=s.state,
                    has_content=s.has_content,
                    is_dirty=s.is_dirty,
                    needs_creation=s.needs_creation,
                )
            )
        return results

    def summary(self) -> dict[str, int]:
        """Return a high-level summary: ``{"healthy": n, "dirty": n, "missing": n}``."""
        counts = {"healthy": 0, "dirty": 0, "missing": 0}
        for s in self.status_detail():
            counts[s.state.value] += 1
        return counts
