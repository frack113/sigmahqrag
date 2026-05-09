"""Tests for core services."""

from __future__ import annotations

import pytest
from src.core.services import (
    HFDownloadService,
    LocalRegistry,
    ModelManager,
    ModelNotFoundError,
    VRAMEstimator,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temp directory."""
    return tmp_path / "test_models"


@pytest.fixture
def registry(temp_dir):
    """Create registry."""
    return LocalRegistry(registry_path=temp_dir / "registry.json")


@pytest.fixture
def download_service(temp_dir):
    """Create download service."""
    return HFDownloadService(temp_dir=temp_dir)


@pytest.fixture
def model_manager(registry, download_service):
    """Create model manager."""
    return ModelManager(registry=registry, download_service=download_service)


@pytest.mark.asyncio
async def test_model_not_found(model_manager):
    """Test model not found error."""
    with pytest.raises(ModelNotFoundError):
        await model_manager.delete_model("nonexistent/model")


@pytest.mark.asyncio
async def test_download_service(temp_dir):
    """Test download service initialization."""
    service = HFDownloadService(temp_dir=temp_dir)
    assert service.temp_dir == temp_dir


@pytest.mark.asyncio
async def test_checksum_verification(temp_dir):
    """Test checksum verification."""
    service = HFDownloadService(temp_dir=temp_dir)
    test_file = temp_dir / "test.gguf"
    test_file.write_bytes(b"test content")

    hash_val = service.compute_checksum(test_file)
    assert len(hash_val) == 64

    is_valid = service.verify_checksum(test_file, hash_val)
    assert is_valid is True

    is_invalid = service.verify_checksum(test_file, "invalid_hash")
    assert is_invalid is False


@pytest.mark.asyncio
async def test_vram_estimator():
    """Test VRAM estimation."""
    estimator = VRAMEstimator()

    result = await estimator.estimate(
        model_size_bytes=700_000_000,
        context_length=2048,
        layers=16,
        heads=32,
        head_dim=128,
    )

    assert "estimated_vram_bytes" in result
    assert result["estimated_vram_bytes"] > 700_000_000


@pytest.mark.asyncio
async def test_vram_estimator_approximation():
    """Test VRAM estimation with missing metadata."""
    estimator = VRAMEstimator()

    result = await estimator.estimate(
        model_size_bytes=700_000_000,
    )

    assert result["is_approximation"] is True


@pytest.mark.asyncio
async def test_vram_compatibility():
    """Test VRAM compatibility check."""
    estimator = VRAMEstimator()

    result = await estimator.check_compatibility(
        model_size_bytes=1_000_000_000,
    )

    assert "is_compatible" in result
    assert "available_vram_bytes" in result
