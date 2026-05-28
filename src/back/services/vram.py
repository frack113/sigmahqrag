"""VRAM estimation service (wrapper for backward compatibility)."""

from src.back.llamacpp.vram import VRAMEstimator


def create_vram_estimator() -> VRAMEstimator:
    """Create a VRAMEstimator instance."""
    return VRAMEstimator()
