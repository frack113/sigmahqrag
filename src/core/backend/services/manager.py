"""Model manager orchestrator service."""

from __future__ import annotations

from src.core.backend.huggingface import HFDownloadService
from src.core.backend.llamacpp.vram import VRAMEstimator
from src.share import LLM_DIR


class DownloadError(Exception):
    """Download operation error."""

    pass


class LocalRegistry:
    """Local registry for models."""

    pass


class ModelFile:
    """Model file."""

    pass


class ModelRecord:
    """Model record."""

    pass


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
        from src.share import MODELS_DIR

        registry_path = MODELS_DIR / "registry.json"
        self.registry = registry or LocalRegistry(registry_path)
        self.download_service = download_service or HFDownloadService()
        self.vram_estimator = VRAMEstimator()
        self.llm_dir = LLM_DIR
        self.llm_dir.mkdir(parents=True, exist_ok=True)

    async def search_models(self, query: str) -> list:
        """Search for models on HuggingFace."""
        return self.download_service.list_models(query)

    async def get_model_info(self, repo_id: str):
        """Get model information."""
        from src.core.types import HFRepo

        return self.download_service.get_model_info(HFRepo.from_string(repo_id))

    async def download_model(
        self,
        repo_id: str,
        filename: str | None = None,
        expected_hash: str | None = None,
    ) -> ModelRecord:
        """Download a model with atomic workflow."""
        from src.core.types import HFRepo

        repo = HFRepo.from_string(repo_id)
        await self.registry.update_status(repo_id, "downloading")

        try:
            final_path = self.download_service.download_gguf(
                repo, self.llm_dir, filename
            )

            await self.registry.update_status(repo_id, "ready")

            if not filename:
                filename = final_path.name

            record = ModelRecord(
                repo_id=repo_id,
                files={
                    filename: ModelFile(
                        filename=filename,
                        local_path=final_path,
                        file_size=final_path.stat().st_size,
                    )
                },
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

    async def delete_model(self, repo_id: str, filename: str | None = None) -> None:
        """Delete a model or specific file."""
        record = await self.registry.get_model(repo_id)
        if not record:
            raise ModelNotFoundError(f"Model {repo_id} not found")

        if filename:
            file_record = record.files.get(filename)
            parent_dir = file_record.local_path.parent if file_record else None
            if file_record and file_record.local_path.exists():
                file_record.local_path.unlink()
            await self.registry.delete_model(repo_id, filename)
            if parent_dir and parent_dir.exists() and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
        else:
            first_file = next(iter(record.files.values()), None)
            parent_dir = first_file.local_path.parent if first_file else None
            for f in record.files.values():
                if f.local_path.exists():
                    f.local_path.unlink()
            await self.registry.delete_model(repo_id)
            if parent_dir and parent_dir.exists() and not any(parent_dir.iterdir()):
                parent_dir.rmdir()

    async def estimate_vram(self, repo_id: str, context_length: int = 2048) -> dict:
        """Estimate VRAM for a model."""
        info = self.get_model_info(repo_id)
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
