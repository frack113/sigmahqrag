"""Model manager orchestrator service."""

from __future__ import annotations

from src.config import LLM_DIR

from .download import AtomicDownloadService, DownloadError, HFDownloadService
from .registry import LocalRegistry, ModelRecord
from .vram import VRAMEstimator


class ModelNotFoundError(Exception):
    """Model not found error."""

    pass


class ModelManager:
    """Orchestrator for model management operations."""

    def __init__(
        self,
        registry: LocalRegistry | None = None,
        download_service: HFDownloadService | None = None,
    ) -> None:
        self.registry = registry or LocalRegistry()
        self.download_service = download_service or HFDownloadService()
        self.atomic_service = AtomicDownloadService(hf_service=self.download_service)
        self.vram_estimator = VRAMEstimator()
        self.llm_dir = LLM_DIR
        self.llm_dir.mkdir(parents=True, exist_ok=True)

    async def search_models(self, query: str) -> list:
        """Search for models on HuggingFace."""
        return await self.download_service.list_models(query)

    async def get_model_info(self, repo_id: str):
        """Get model information."""
        return await self.download_service.get_model_info(repo_id)

    async def download_model(
        self,
        repo_id: str,
        filename: str | None = None,
        expected_hash: str | None = None,
    ) -> ModelRecord:
        """Download a model with atomic workflow."""
        await self.registry.update_status(repo_id, "downloading")

        try:
            final_path = await self.atomic_service.download_atomic(
                repo_id, filename, expected_hash
            )

            await self.registry.update_status(repo_id, "ready")

            record = ModelRecord(
                repo_id=repo_id,
                local_path=final_path,
                file_size=final_path.stat().st_size,
                status="ready",
            )
            await self.registry.register_model(record)
            return record
        except Exception as e:
            await self.registry.update_status(repo_id, "error", str(e))
            raise DownloadError(f"Download failed: {e}") from e

    async def list_installed_models(self) -> list[ModelRecord]:
        """List all installed models."""
        return await self.registry.list_models()

    async def delete_model(self, repo_id: str) -> None:
        """Delete a model."""
        record = await self.registry.get_model(repo_id)
        if not record:
            raise ModelNotFoundError(f"Model {repo_id} not found")

        if record.local_path.exists():
            record.local_path.unlink()

        await self.registry.delete_model(repo_id)

    async def estimate_vram(self, repo_id: str, context_length: int = 2048) -> dict:
        """Estimate VRAM for a model."""
        info = await self.get_model_info(repo_id)
        if not info:
            raise ModelNotFoundError(f"Model {repo_id} not found")

        size = 0
        if info.siblings:
            for f in info.siblings:
                if f.rfilename.endswith(".gguf"):
                    size = f.size or 0
                    break

        return await self.vram_estimator.check_compatibility(
            model_size_bytes=size,
            context_length=context_length,
        )
