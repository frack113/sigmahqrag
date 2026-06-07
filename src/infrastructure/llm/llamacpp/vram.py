"""VRAM estimation service for llama.cpp models."""

from __future__ import annotations


class VRAMEstimator:
    """Estimates VRAM requirements for model inference."""

    DEFAULT_OVERHEAD = 1.15
    DEFAULT_BUFFER_MB = 512

    def __init__(
        self,
        overhead_coeff: float = DEFAULT_OVERHEAD,
        buffer_mb: int = DEFAULT_BUFFER_MB,
    ) -> None:
        self.overhead_coeff = overhead_coeff
        self.buffer_mb = buffer_mb
        self._available_vram: int | None = None

    async def estimate(
        self,
        model_size_bytes: int,
        context_length: int = 2048,
        layers: int | None = None,
        heads: int | None = None,
        head_dim: int | None = None,
        precision_bytes: int = 2,
    ) -> dict:
        """Estimate VRAM requirements."""
        bytes_per_gb = 1024 * 1024 * 1024

        model_vram = int(model_size_bytes * self.overhead_coeff)

        if layers and heads and head_dim:
            kv_cache = 2 * layers * heads * head_dim * precision_bytes * context_length
        else:
            kv_cache = int(model_size_bytes * 0.1)

        buffer = max(self.buffer_mb * 1024 * 1024, model_vram * 0.1)
        total_vram = model_vram + kv_cache + buffer
        approximated = layers is None or heads is None or head_dim is None

        return {
            "model_size_bytes": int(model_size_bytes),
            "estimated_vram_bytes": int(total_vram),
            "estimated_vram_gb": round(total_vram / bytes_per_gb, 2),
            "context_length": context_length,
            "is_approximation": approximated,
            "components": {
                "model_vram_bytes": int(model_vram),
                "kv_cache_bytes": int(int(kv_cache)),
                "buffer_bytes": int(int(buffer)),
            },
        }

    async def get_available_vram(self) -> int:
        """Get available VRAM from GPU."""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.free",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self._available_vram = int(result.stdout.strip()) * 1024 * 1024
        except Exception:
            pass

        if self._available_vram is None:
            self._available_vram = 8 * 1024 * 1024 * 1024

        return self._available_vram

    async def check_compatibility(
        self,
        model_size_bytes: int,
        context_length: int = 2048,
        **model_meta,
    ) -> dict:
        """Check if model fits in available VRAM."""
        estimate = await self.estimate(model_size_bytes, context_length, **model_meta)
        available = await self.get_available_vram()
        is_compatible = estimate["estimated_vram_bytes"] <= available

        return {
            **estimate,
            "available_vram_bytes": available,
            "available_vram_gb": round(available / (1024**3), 2),
            "is_compatible": is_compatible,
        }


def create_vram_estimator() -> VRAMEstimator:
    """Create a VRAMEstimator instance."""
    return VRAMEstimator()
