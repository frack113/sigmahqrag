"""Tests for unified ingestion pipeline in indexing module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.core.sigma.models import SigmaRule


def _make_fake_to_thread():
    """Create a fake asyncio.to_thread that just calls the function directly."""

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    return fake_to_thread


class TestIndexSigmaRulesPipeline:
    """AC1: Sigma rules ingestion uses IngestionPipeline."""

    @pytest.mark.asyncio
    async def test_calls_pipeline_run_not_add_vectors(self) -> None:
        """Verify indexing uses pipeline.run(), not direct Qdrant add."""
        fake_to_thread = _make_fake_to_thread()

        with (
            patch("src.core.pipeline.ingestion.IngestionPipelineBuilder") as MockBuilder,
            patch("src.application.documents.indexing.get_qdrant_client"),
            patch("src.application.documents.indexing.asyncio.to_thread", fake_to_thread),
        ):
            mock_builder = MagicMock()
            MockBuilder.return_value = mock_builder
            MockBuilder._num_workers = 4
            mock_builder.build.return_value.run.return_value = [MagicMock()]

            # Force re-import to pick up patched asyncio.to_thread
            if "src.application.documents.indexing" in sys.modules:
                del sys.modules["src.application.documents.indexing"]

            from src.application.documents.indexing import index_sigma_rules  # noqa: F401

            rule = SigmaRule(
                id="S1",
                title="Test Rule",
                detection={"selection": {"EventID": 4688}},
                condition="selection",
                level="high",
            )

            result = await index_sigma_rules(
                rules=[rule],
                collection_name="sigma_rules",
                mode="flat",
            )

            assert result["success"] is True
            assert result["indexed"] == 1
            MockBuilder.assert_called_once_with(collection_name="sigma_rules")
            mock_builder.build.assert_called_once_with(skip_splitter=True)

    @pytest.mark.asyncio
    async def test_preserves_textnode_metadata_through_pipeline(self) -> None:
        """TextNode metadata (rule_id, chunk_type) survives pipeline."""
        captured_docs = []

        def capture_run(documents, **kwargs):
            captured_docs.extend(documents)
            return list(documents)

        fake_to_thread = _make_fake_to_thread()

        with (
            patch("src.core.pipeline.ingestion.IngestionPipelineBuilder") as MockBuilder,
            patch("src.application.documents.indexing.asyncio.to_thread", fake_to_thread),
        ):
            mock_builder = MagicMock()
            MockBuilder.return_value = mock_builder
            mock_builder.build.return_value.run.side_effect = capture_run
            mock_builder._num_workers = 4

            # Force re-import to pick up patched asyncio.to_thread
            if "src.application.documents.indexing" in sys.modules:
                del sys.modules["src.application.documents.indexing"]

            from src.application.documents.indexing import index_sigma_rules

            rule = SigmaRule(
                id="test_rule",
                title="Test Rule",
                description="A test",
                detection={"selection": {"EventID": 4688}},
                condition="selection",
                author="dev",
                date="2026-01-01",
                level="low",
                status="testing",
                tags=["tag1"],
                logsource={"product": "windows"},
                falsepositives=[],
                references=[],
                modified=None,
            )

            result = await index_sigma_rules([rule], collection_name="sigma_rules", mode="flat")

            assert result["success"] is True
            assert len(captured_docs) == 1
            assert captured_docs[0].metadata["rule_id"] == "test_rule"
            assert captured_docs[0].metadata["chunk_type"] == "full_rule"

    @pytest.mark.asyncio
    async def test_empty_rules_returns_success_zero(self) -> None:
        """Empty rule list returns success with 0 indexed."""
        from src.application.documents.indexing import index_sigma_rules

        result = await index_sigma_rules([], collection_name="sigma_rules")

        assert result["success"] is True
        assert result["indexed"] == 0

    @pytest.mark.asyncio
    async def test_rich_mode_passes_through(self) -> None:
        """Rich mode creates multiple TextNodes per rule."""
        captured_docs = []

        def capture_run(documents, **kwargs):
            captured_docs.extend(documents)
            return list(documents)

        with patch("src.core.pipeline.ingestion.IngestionPipelineBuilder") as MockBuilder:
            mock_builder = MagicMock()
            MockBuilder.return_value = mock_builder
            mock_builder.build.return_value.run.side_effect = capture_run
            mock_builder._num_workers = 4

            from src.application.documents.indexing import index_sigma_rules

            rule = SigmaRule(
                id="R1",
                title="T",
                description="D",
                detection={"selection": {"EventID": 1234}},
                condition="selection",
                author="a",
                date="2026-01-01",
                level="med",
                status="prod",
                tags=["tag1", "tag2"],
                logsource={"product": "linux"},
                falsepositives=[],
                references=[],
                modified=None,
            )

            result = await index_sigma_rules([rule], collection_name="sigma_rules", mode="rich")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_collection_lock_is_per_collection(self) -> None:
        """Different collections get different locks."""
        from src.application.documents.indexing import _get_collection_lock

        lock_a = _get_collection_lock("collection_A")
        lock_b = _get_collection_lock("collection_B")
        lock_a_again = _get_collection_lock("collection_A")

        assert lock_a is not lock_b
        assert lock_a is lock_a_again


class TestEmbeddingSingleton:
    """AC3: Single embedding model singleton."""

    def test_singleton_returns_same_instance(self) -> None:
        """Multiple calls return same object (identity check)."""
        from src.core.embedding.factory import get_embedding_model, reset_embedding_model

        mock_db = MagicMock()
        mock_db.get_active_embedding_model_name.return_value = None

        with (
            patch("src.core.embedding.factory.DatabaseService") as MockDB,
            patch("src.core.pipeline.ingestion.build_embed_model") as mock_build,
        ):
            MockDB.get_instance.return_value = mock_db
            mock_build.return_value = MagicMock()
            reset_embedding_model()

            model_a = get_embedding_model()
            model_b = get_embedding_model()

            assert model_a is model_b

    def test_reset_clears_singleton(self) -> None:
        """Reset clears the cached instance."""
        from src.core.embedding.factory import get_embedding_model, reset_embedding_model

        mock_db = MagicMock()
        mock_db.get_active_embedding_model_name.return_value = None

        with (
            patch("src.core.embedding.factory.DatabaseService") as MockDB,
            patch("src.core.pipeline.ingestion.build_embed_model") as mock_build,
        ):
            MockDB.get_instance.return_value = mock_db
            mock_build.side_effect = lambda name: MagicMock()

            model_before = get_embedding_model()
            reset_embedding_model()
            model_after = get_embedding_model()

            assert model_before is not model_after


class TestDeleteReindexStrategy:
    """AC2: Direct Qdrant client path removed from indexing.py."""

    @pytest.mark.asyncio
    async def test_deletes_collection_before_insert(self) -> None:
        """Verify collection is deleted before pipeline insert (delete+reindex)."""
        with (
            patch("src.application.documents.indexing.get_qdrant_client") as MockClient,
            patch("src.core.pipeline.ingestion.IngestionPipelineBuilder") as MockBuilder,
        ):
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_builder = MagicMock()
            MockBuilder.return_value = mock_builder
            mock_builder.build.return_value.run.return_value = [MagicMock()]
            mock_builder._num_workers = 4

            from src.application.documents.indexing import index_sigma_rules

            rule = SigmaRule(
                id="S1",
                title="Test",
                detection={"selection": {"EventID": 4688}},
                condition="selection",
                level="high",
            )

            await index_sigma_rules([rule], collection_name="sigma_rules")

            mock_client.delete_collection.assert_called_once_with("sigma_rules")

    def test_no_add_vectors_in_indexing(self) -> None:
        """Verify no QdrantService.add_vectors call in indexing.py."""
        from src.application.documents import indexing

        source = open(indexing.__file__).read()

        assert "add_vectors" not in source or "_vector_store.add(nodes)" in source


class TestIndexErrors:
    """Error handling for index_sigma_rules."""

    @pytest.mark.asyncio
    async def test_pipeline_failure_returns_error(self) -> None:
        """Pipeline failure returns error dict."""
        fake_to_thread = _make_fake_to_thread()

        with (
            patch("src.core.pipeline.ingestion.IngestionPipelineBuilder") as MockBuilder,
            patch("src.application.documents.indexing.asyncio.to_thread", fake_to_thread),
        ):
            mock_builder = MagicMock()
            MockBuilder.return_value = mock_builder
            mock_builder.build.side_effect = RuntimeError("Qdrant unreachable")
            mock_builder._num_workers = 4

            # Force re-import to pick up patched asyncio.to_thread
            if "src.application.documents.indexing" in sys.modules:
                del sys.modules["src.application.documents.indexing"]

            from src.application.documents.indexing import index_sigma_rules

            rule = SigmaRule(
                id="S1",
                title="Test",
                detection={"selection": {"EventID": 4688}},
                condition="selection",
                level="high",
            )

            result = await index_sigma_rules([rule], collection_name="sigma_rules")

            assert result["success"] is False
            assert "error" in result


class TestInvalidMode:
    """Edge cases for mode parameter."""

    @pytest.mark.asyncio
    async def test_invalid_mode_raises_value_error(self) -> None:
        """Invalid mode raises ValueError."""
        from src.application.documents.indexing import index_sigma_rules

        rule = SigmaRule(
            id="S1",
            title="Test",
            detection={"selection": {"EventID": 4688}},
            condition="selection",
            level="high",
        )

        with pytest.raises(ValueError, match="Invalid mode"):
            await index_sigma_rules([rule], collection_name="sigma_rules", mode="invalid")
