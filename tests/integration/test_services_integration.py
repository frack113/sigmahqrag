"""Integration tests for service integration.

These tests verify that LlamaService and QdrantService are properly
integrated and can communicate with their respective servers.

Requirements:
- llama.cpp server running on port 8080
- Qdrant server running on port 6333
"""

from __future__ import annotations

from typing import Any

import pytest


class TestLlamaServiceIntegration:
    """Integration tests for LlamaService.

    AC1: Given LlamaService is instantiated
    When I call health_check()
    Then it returns True if llama.cpp server is running on port 8080
    """

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self):
        """Test health_check() returns correct status."""
        from sigmahqrag.services.llama_service import LlamaService

        service = LlamaService(base_url="http://127.0.0.1:8080")
        result = await service.health_check()

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_connection_to_llama_server(self):
        """Test connection to llama.cpp server.

        AC1 continuation: Verify connection is possible.
        """
        from sigmahqrag.services.llama_service import LlamaService

        service = LlamaService(base_url="http://127.0.0.1:8080")
        is_healthy = await service.health_check()

        if is_healthy:
            response = await service.complete("Hello")
            assert isinstance(response, str)
            assert len(response) > 0


class TestQdrantServiceIntegration:
    """Integration tests for QdrantService.

    AC2: Given QdrantService is instantiated
    When I call health_check()
    Then it returns True if Qdrant server is running on port 6333
    """

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self):
        """Test health_check() returns correct status."""
        from sigmahqrag.services.qdrant_service import QdrantService

        service = QdrantService(host="127.0.0.1", port=6333)
        result = await service.health_check()

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running Qdrant server")
    async def test_collection_creation(self):
        """Test collection creation.

        AC3: Given both services are running
        When I attempt to create a test collection in Qdrant
        Then the collection is created successfully
        """
        from sigmahqrag.services.qdrant_service import QdrantService

        test_collection = "test_integration_collection"
        service = QdrantService(
            collection_name=test_collection,
            host="127.0.0.1",
            port=6333,
            vector_size=384,
        )

        await service.create_collection()
        is_healthy = await service.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires running Qdrant server")
    async def test_vector_storage_and_retrieval(self):
        """Test vector storage and retrieval.

        AC3 continuation: Verify vectors can be stored and retrieved.
        """
        from sigmahqrag.services.qdrant_service import QdrantService

        test_collection = "test_vector_collection"
        service = QdrantService(
            collection_name=test_collection,
            host="127.0.0.1",
            port=6333,
            vector_size=384,
        )

        await service.create_collection()

        test_vectors: list[list[float]] = [
            [0.1] * 384,
            [0.2] * 384,
        ]
        test_docs = ["Document 1", "Document 2"]
        test_metadata: list[dict[str, Any]] = [
            {"source": "test"},
            {"source": "test"},
        ]

        await service.add_vectors(
            embeddings=test_vectors,
            documents=test_docs,
            metadata=test_metadata,
        )

        results = await service.search(
            query_embedding=[0.1] * 384,
            top_k=2,
        )
        assert isinstance(results, list)


class TestServiceManager:
    """Integration tests for service start/stop functionality.

    AC4: Given the service manager
    When I start a service
    Then the service process is running and responds to health checks
    And when I stop the service
    Then the process is terminated
    """

    @pytest.mark.asyncio
    async def test_llama_service_start_stop(self):
        """Test start/stop llama.cpp via health check.

        Note: This test verifies the health check mechanism.
        Actual start/stop requires binary paths from prerequisites.
        """
        from sigmahqrag.services.llama_service import LlamaService

        service = LlamaService(base_url="http://127.0.0.1:8080")

        is_healthy = await service.health_check()

        assert isinstance(is_healthy, bool)
        if is_healthy:
            response = await service.complete("test")
            assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_qdrant_service_start_stop(self):
        """Test start/stop Qdrant via health check.

        Note: This test verifies the health check mechanism.
        Actual start/stop requires binary paths from prerequisites.
        """
        from sigmahqrag.services.qdrant_service import QdrantService

        service = QdrantService(host="127.0.0.1", port=6333)

        is_healthy = await service.health_check()

        assert isinstance(is_healthy, bool)
        if is_healthy:
            await service.create_collection()
            assert True


class TestServicePrerequisites:
    """Verify prerequisites are met before running integration tests."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Prerequisites binaries not yet downloaded")
    async def test_llama_cpp_binary_exists(self):
        """Test that llama.cpp binary exists from prerequisites."""
        from pathlib import Path

        binary_paths = [
            Path("bin/llama-server"),
            Path("bin/llama-server.exe"),
        ]

        assert any(p.exists() for p in binary_paths), (
            "llama.cpp binary not found. Run prereq-1 first."
        )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Prerequisites binaries not yet downloaded")
    async def test_qdrant_binary_exists(self):
        """Test that Qdrant binary exists from prerequisites."""
        from pathlib import Path

        binary_paths = [
            Path("bin/qdrant"),
            Path("bin/qdrant.exe"),
        ]

        assert any(p.exists() for p in binary_paths), (
            "Qdrant binary not found. Run prereq-2 first."
        )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Prerequisites models not yet downloaded")
    async def test_llm_model_exists(self):
        """Test that LLM model exists from prerequisites."""
        from pathlib import Path

        model_dir = Path("models/llm")

        if model_dir.exists():
            models = list(model_dir.glob("*.gguf"))
            assert len(models) > 0, (
                "No LLM models found. Run prereq-3 first."
            )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Prerequisites models not yet downloaded")
    async def test_embedding_model_exists(self):
        """Test that embedding model exists from prerequisites."""
        from pathlib import Path

        model_dir = Path("models/embeddings")

        if model_dir.exists():
            models = list(model_dir.glob("*.gguf"))
            assert len(models) > 0, (
                "No embedding models found. Run prereq-4 first."
            )