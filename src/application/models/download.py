"""Download service for HuggingFace models."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from src.application.models.exceptions import DownloadError
from src.application.models.types import HFRepo
from src.config.settings import TEMP_DIR
from src.infrastructure.database.service import DatabaseService


class HFDownloadService:
    """Service for downloading models from HuggingFace."""

    def __init__(
        self,
        temp_dir: Path | None = None,
        token: str | None = None,
    ) -> None:
        self.temp_dir = temp_dir or TEMP_DIR
        self.token = token or os.environ.get("HF_TOKEN")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._metadata: dict[str, dict] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load download metadata from DuckDB."""
        try:
            data = DatabaseService.get_instance().get_config("download_metadata")
            if data:
                self._metadata = data
        except RuntimeError:
            pass

    def list_gguf_files(
        self,
        repo: HFRepo,
    ) -> list[dict[str, Any]]:
        """List all .gguf files in a repository with metadata."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        try:
            info = api.model_info(repo_id=repo.full_id, files_metadata=True)
            siblings = info.siblings or []

            results = []
            for f in siblings:
                if f.rfilename.endswith(".gguf"):
                    results.append(
                        {
                            "filename": f.rfilename,
                            "size": f.size or 0,
                        }
                    )
            return results
        except Exception as e:
            raise DownloadError(f"Failed to list GGUF files for {repo.full_id}: {e}") from e

    def get_model_info(self, repo: HFRepo):
        """Get model info from HuggingFace."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        return api.model_info(repo_id=repo.full_id)

    def download_repo(self, repo: HFRepo, target_dir: Path) -> Path:
        """Download an entire repository."""
        from huggingface_hub import snapshot_download

        path = snapshot_download(
            repo_id=repo.full_id,
            local_dir=target_dir,
            token=self.token,
        )
        return Path(path)

    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify file checksum."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest() == expected_sha256

    def compute_checksum(self, file_path: Path) -> str:
        """Compute file SHA256."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    async def list_models(self, query: str, task: str | None = None) -> list[HFRepo]:
        """Search for models on HuggingFace.

        Args:
            query: Search query string.
            task: Optional pipeline tag filter (e.g. ``"feature-extraction"``
                for embedding models, ``"text-generation"`` for LLMs).

        Returns:
            List of matching :class:`HFRepo` instances.
        """
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        kwargs: dict[str, Any] = {"search": query, "sort": "downloads"}
        if task:
            kwargs["pipeline_tag"] = task
        try:
            results = api.list_models(**kwargs)
            return [HFRepo.from_string(r.id) for r in results]
        except Exception as e:
            raise DownloadError(f"Failed to search models: {e}") from e
