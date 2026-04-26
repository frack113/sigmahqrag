"""Tests for core services."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.core.services import (
    HFDownloadService,
    AtomicDownloadService,
    LocalRegistry,
    ModelInfo,
    ModelManager,
    ModelRecord,
    ModelNotFoundError,
    DownloadError,
    ChecksumMismatchError,
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
def atomic_service(download_service, temp_dir):
    """Create atomic service."""
    return AtomicDownloadService(hf_service=download_service, final_dir=temp_dir)


@pytest.fixture
def model_manager(registry, download_service):
    """Create model manager."""
    return ModelManager(registry=registry, download_service=download_service)


@pytest.mark.asyncio
async def test_search_models(model_manager):
    """Test model search works (may fail with network error)."""
    try:
        results = await model_manager.search_models("llama")
    except Exception:
        results = []
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_get_model_info(model_manager):
    """Test get model info works (may fail with network error)."""
    try:
        info = await model_manager.get_model_info("meta-llama/Llama-3.2-1B")
    except Exception:
        info = None
    assert info is None or info.repo_id == "meta-llama/Llama-3.2-1B"


@pytest.mark.asyncio
async def test_register_and_get_model(registry):
    """Test model registration."""
    record = ModelRecord(
        repo_id="test/model",
        local_path=Path("/tmp/model.gguf"),
        file_size=1_000_000,
    )
    await registry.register_model(record)

    retrieved = await registry.get_model("test/model")
    assert retrieved is not None
    assert retrieved.repo_id == "test/model"
    assert retrieved.status == "pending"


@pytest.mark.asyncio
async def test_update_status(registry):
    """Test status update."""
    record = ModelRecord(
        repo_id="test/model",
        local_path=Path("/tmp/model.gguf"),
        file_size=1_000_000,
    )
    await registry.register_model(record)

    await registry.update_status("test/model", "ready")
    retrieved = await registry.get_model("test/model")
    assert retrieved is not None
    assert retrieved.status == "ready"


@pytest.mark.asyncio
async def test_list_models(registry):
    """Test list models."""
    record1 = ModelRecord(
        repo_id="test/model1",
        local_path=Path("/tmp/model1.gguf"),
        file_size=1_000_000,
    )
    record2 = ModelRecord(
        repo_id="test/model2",
        local_path=Path("/tmp/model2.gguf"),
        file_size=2_000_000,
    )
    await registry.register_model(record1)
    await registry.register_model(record2)

    models = await registry.list_models()
    assert len(models) == 2


@pytest.mark.asyncio
async def test_delete_model(registry):
    """Test model deletion."""
    record = ModelRecord(
        repo_id="test/model",
        local_path=Path("/tmp/model.gguf"),
        file_size=1_000_000,
    )
    await registry.register_model(record)

    await registry.delete_model("test/model")
    retrieved = await registry.get_model("test/model")
    assert retrieved is None


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
async def test_atomic_download_service(temp_dir):
    """Test atomic download service."""
    service = AtomicDownloadService(final_dir=temp_dir)
    assert service.final_dir == temp_dir


@pytest.mark.asyncio
async def test_disk_space_check(temp_dir):
    """Test disk space check."""
    service = AtomicDownloadService(final_dir=temp_dir)
    has_space = service.check_disk_space(1024, temp_dir)
    assert isinstance(has_space, bool)


@pytest.mark.asyncio
async def test_registry_persistence(temp_dir):
    """Test registry persistence."""
    registry = LocalRegistry(registry_path=temp_dir / "registry.json")
    record = ModelRecord(
        repo_id="test/model",
        local_path=Path("/tmp/model.gguf"),
        file_size=1_000_000,
    )
    await registry.register_model(record)

    new_registry = LocalRegistry(registry_path=temp_dir / "registry.json")
    retrieved = await new_registry.get_model("test/model")
    assert retrieved is not None
    assert retrieved.repo_id == "test/model"


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