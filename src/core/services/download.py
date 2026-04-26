"""Download services for HuggingFace models."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.config import LLM_DIR


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
        self.temp_dir = temp_dir or Path("temp/downloads")
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
        repo_id: str,
    ) -> list[dict[str, Any]]:
        """List all .gguf files in a repository with metadata."""

        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        try:
            files = api.list_repo_files(repo_id=repo_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]

            results = []
            for filename in gguf_files:
                # Get file size from metadata if possible, or use a placeholder
                # Note: list_repo_files doesn't give sizes directly,
                # but we can use model_info to get file details in a more complex way if needed.
                # For now, we return the filename.
                results.append({
                    "filename": filename,
                    "name": filename, # For display
                })
            return results
        except Exception as e:
            raise DownloadError(f"Failed to list GGUF files: {e}") from e

    def get_model_info(self, repo_id: str):
        """Get model info from HuggingFace."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.token)
        return api.model_info(repo_id)

    def download(self, repo_id: str, target_dir: Path, filename: str | None = None, is_embedding: bool = False) -> Path:
        """Download model/embeddings using the direct local_dir strategy."""
        from huggingface_hub import hf_hub_download, snapshot_download

        target_dir.mkdir(parents=True, exist_ok=True)

        if is_embedding:
            # For embeddings, we download the whole repo
            path = snapshot_download(
                repo_id=repo_id,
                local_dir=target_dir,
                local_dir_use_symlinks=False,
                token=self.token,
            )
            return Path(path)
        else:
            # For LLMs (GGUF), we download a specific file
            if filename is None:
                info = self.get_model_info(repo_id)
                if info.siblings:
                    for f in info.siblings:
                        if f.rfilename.endswith(".gguf"):
                            filename = f.rfilename
                            break

            if filename is None:
                raise DownloadError(f"No GGUF file found for {repo_id}")

            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
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

    def cancel_download(self, repo_id: str) -> None:
        """Cancel and cleanup pending download."""
        if repo_id in self._metadata:
            temp_path = self._metadata[repo_id].get("temp_path")
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()
            del self._metadata[repo_id]
            self._save_metadata()


class AtomicDownloadService:
    """Atomic download with checksum verification."""

    def __init__(
        self,
        hf_service: HFDownloadService | None = None,
        final_dir: Path | None = None,
    ) -> None:
        self.hf_service = hf_service or HFDownloadService()
        self.final_dir = final_dir or LLM_DIR
        self.final_dir.mkdir(parents=True, exist_ok=True)

    async def download_atomic(
        self,
        repo_id: str,
        filename: str | None = None,
        expected_hash: str | None = None,
        is_embedding: bool = False,
    ) -> Path:
        """Download with atomic workflow."""
        import shutil

        if is_embedding:
            final_dest = self.final_dir / repo_id.replace("/", "_")
        else:
            final_dest = self.final_dir / repo_id.replace("/", "_") / (filename if filename else "model.gguf")

        # Define a temporary download directory within the final destination to ensure atomicity
        tmp_download_dir = self.final_dir / ".tmp" / repo_id.replace("/", "_")
        tmp_download_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Download into the temp directory
            downloaded_path = self.hf_service.download(repo_id, target_dir=tmp_download_dir, filename=filename, is_embedding=is_embedding)

            # 2. Verify checksum if provided (only for single files like GGUF)
            if not is_embedding and expected_hash:
                is_valid = self.hf_service.verify_checksum(downloaded_path, expected_hash)
                if not is_valid:
                    raise ChecksumMismatchError(f"Checksum mismatch for {repo_id}")

            # 3. Move from temp to final destination
            final_dest.parent.mkdir(parents=True, exist_ok=True)

            if is_embedding:
                # For embeddings, we move the entire directory
                if final_dest.exists():
                    shutil.rmtree(final_dest)
                shutil.move(str(tmp_download_dir), str(final_dest))
                actual_dest = final_dest
            else:
                # For GGUF, we move the single file
                if final_dest.exists():
                    final_dest.unlink()
                shutil.move(str(downloaded_path), str(final_dest))
                actual_dest = final_dest

            return actual_dest

        except Exception as e:
            # Cleanup on failure
            if tmp_download_dir.exists():
                if tmp_download_dir.is_dir():
                    shutil.rmtree(tmp_download_dir)
                else:
                    tmp_download_dir.unlink()
            raise DownloadError(f"Atomic download failed for {repo_id}: {e}") from e

    def check_disk_space(self, required_bytes: int, path: Path) -> bool:
        """Check available disk space."""
        import shutil

        stat = shutil.disk_usage(path)
        return stat.free >= required_bytes
