"""Download services for HuggingFace models."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.back.backend.huggingface.types import HFRepo


class DownloadError(Exception):
    """Download operation error."""

    pass


class ChecksumMismatchError(DownloadError):
    """Checksum verification failed."""

    pass


class DiskSpaceError(DownloadError):
    """Insufficient disk space."""

    pass


class NetworkError(DownloadError):
    """Network operation failed."""

    pass


class HFDownloadService:
    """Service for downloading models from HuggingFace."""

    def __init__(
        self,
        temp_dir: Path | None = None,
        token: str | None = None,
    ) -> None:
        self.temp_dir = temp_dir or Path("data/temp/downloads")
        self.token = token or os.environ.get("HF_TOKEN")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_path = self.temp_dir / "metadata.json"
        self._metadata: dict[str, dict] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load download metadata from disk."""
        if self._metadata_path.exists():
            with open(self._metadata_path) as f:
                self._metadata = json.load(f)

    def _save_metadata(self) -> None:
        """Save download metadata to disk."""
        self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._metadata_path, "w") as f:
            json.dump(self._metadata, f, indent=2)

    def list_gguf_files(
        self,
        repo: HFRepo,
    ) -> list[dict[str, Any]]:
        """List all .gguf files in a repository with metadata."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        try:
            info = api.model_info(repo_id=repo.full_id)
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
            raise DownloadError(
                f"Failed to list GGUF files for {repo.full_id}: {e}"
            ) from e

    def get_model_info(self, repo: HFRepo):
        """Get model info from HuggingFace."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        return api.model_info(repo_id=repo.full_id)

    def download_gguf(
        self, repo: HFRepo, target_dir: Path, filename: str | None = None
    ) -> Path:
        """Download a GGUF file."""
        from huggingface_hub import hf_hub_download

        if filename is None:
            info = self.get_model_info(repo)
            if info.siblings:
                for f in info.siblings:
                    if f.rfilename.endswith(".gguf"):
                        filename = f.rfilename
                        break

        if filename is None:
            raise DownloadError(f"No GGUF file found for {repo.full_id}")

        model_dir = target_dir / repo.owner / repo.name
        model_dir.mkdir(parents=True, exist_ok=True)

        path = hf_hub_download(
            repo_id=repo.full_id,
            filename=filename,
            local_dir=model_dir,
            local_dir_use_symlinks=False,
            token=self.token,
        )
        return Path(path)

    def download_repo(self, repo: HFRepo, target_dir: Path) -> Path:
        """Download an entire repository."""
        from huggingface_hub import snapshot_download

        path = snapshot_download(
            repo_id=repo.full_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
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

    def get_pending_downloads(self) -> dict:
        """Get pending downloads."""
        return self._metadata

    async def list_models(self, query: str) -> list[HFRepo]:
        """Search for models on HuggingFace."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        try:
            results = api.hf_hub_search(query, sort="downloads", direction=-1)
            return [HFRepo.from_id(r.id) for r in results]
        except Exception as e:
            raise DownloadError(f"Failed to search models: {e}") from e


def create_download_service() -> HFDownloadService:
    """Create an HFDownloadService instance."""
    return HFDownloadService()
