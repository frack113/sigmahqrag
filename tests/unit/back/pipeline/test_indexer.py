"""Tests for UnifiedIndexer with IngestionPipelineBuilder path."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestUnifiedIndexerIngestionPath:
    """Test UnifiedIndexer.index() uses IngestionPipelineBuilder.run()."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.get_pending_by_content_type.return_value = [
            {
                "file_name": "test_rule.yaml",
                "url_hash": "abc123",
                "org": "local",
                "repo": "",
            }
        ]
        db.update_doc_registry_embed_status.return_value = None
        return db

    @pytest.fixture
    def mock_transform(self):
        transform_cls = MagicMock()
        doc = MagicMock()
        doc.text = "Test document text"
        doc.metadata = {"source_file": "test_rule.yaml"}
        transform_cls.return_value.run.return_value = [doc]
        return transform_cls

    @pytest.fixture
    def mock_builder(self):
        builder = MagicMock()
        builder.build.return_value = None
        builder.run.return_value = [MagicMock()]
        return builder

    @pytest.mark.asyncio
    async def test_index_uses_pipeline_run(self, mock_db, mock_transform, mock_builder, tmp_path):
        from src.core.base import TransformConfig

        test_file = tmp_path / "test_rule.yaml"
        test_file.write_text("rule")

        with patch(
            "src.core.pipeline.indexer.TransformRegistry.find_for_file",
            return_value=mock_transform,
        ):
            with patch(
                "src.core.document.parser.generic_parser.GenericTransform._build_default_config",
                return_value=TransformConfig(),
            ):
                with patch(
                    "src.core.pipeline.indexer.IngestionPipelineBuilder",
                    return_value=mock_builder,
                ):
                    with patch.object(mock_db, "_resolve_path_for_test", return_value=test_file):
                        from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

                        indexer = UnifiedIndexer(db=mock_db)
                        # Patch _resolve_path on the instance to return tmp_path file
                        original_resolve = indexer._resolve_path
                        indexer._resolve_path = MagicMock(return_value=test_file)
                        try:
                            result = await indexer.index(ROUTES[0])
                        finally:
                            indexer._resolve_path = original_resolve

        assert result.processed == 1
        mock_db.update_doc_registry_embed_status.assert_called_with("abc123", "embedded")
        mock_builder.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_skips_empty_docs(self, mock_db, tmp_path):
        from src.core.base import TransformConfig

        mock_transform = MagicMock()
        empty_doc = MagicMock()
        empty_doc.text = ""
        empty_doc.metadata = {"source_file": "test.yaml"}
        mock_transform.return_value.run.return_value = [empty_doc]

        test_file = tmp_path / "test.yaml"
        test_file.write_text("rule")

        with patch(
            "src.core.pipeline.indexer.TransformRegistry.find_for_file",
            return_value=mock_transform,
        ):
            with patch(
                "src.core.document.parser.generic_parser.GenericTransform._build_default_config",
                return_value=TransformConfig(),
            ):
                with patch(
                    "src.core.pipeline.indexer.IngestionPipelineBuilder"
                ) as mock_builder_cls:
                    mock_db.update_doc_registry_embed_status.return_value = None

                    from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

                    indexer = UnifiedIndexer(db=mock_db)
                    indexer._resolve_path = MagicMock(return_value=test_file)
                    result = await indexer.index(ROUTES[0])

        assert result.processed == 0
        mock_builder_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_handles_pipeline_no_nodes(self, mock_db, tmp_path):
        from src.core.base import TransformConfig

        mock_transform = MagicMock()
        doc = MagicMock()
        doc.text = "Has text"
        doc.metadata = {"source_file": "test.yaml"}
        mock_transform.return_value.run.return_value = [doc]

        mock_builder = MagicMock()
        mock_builder.run.return_value = []

        test_file = tmp_path / "test.yaml"
        test_file.write_text("rule")

        with patch(
            "src.core.pipeline.indexer.TransformRegistry.find_for_file",
            return_value=mock_transform,
        ):
            with patch(
                "src.core.document.parser.generic_parser.GenericTransform._build_default_config",
                return_value=TransformConfig(),
            ):
                with patch(
                    "src.core.pipeline.indexer.IngestionPipelineBuilder",
                    return_value=mock_builder,
                ):
                    mock_db.update_doc_registry_embed_status.return_value = None

                    from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

                    indexer = UnifiedIndexer(db=mock_db)
                    indexer._resolve_path = MagicMock(return_value=test_file)
                    result = await indexer.index(ROUTES[0])

        assert result.processed == 0
        mock_db.update_doc_registry_embed_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_no_pending_returns_zero(self, mock_db):
        mock_db.get_pending_by_content_type.return_value = []

        from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

        indexer = UnifiedIndexer(db=mock_db)
        result = await indexer.index(ROUTES[0])

        assert result.processed == 0


class TestUnifiedIndexerIndexAll:
    """Test UnifiedIndexer.index_all() routing."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_index_all_filters_by_group_spec(self, mock_db):
        from dataclasses import dataclass

        from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

        @dataclass
        class FakeResult:
            route: object

        with patch.object(UnifiedIndexer, "index", new_callable=AsyncMock) as mock_index:
            mock_index.return_value = FakeResult(route=ROUTES[2])
            indexer = UnifiedIndexer(db=mock_db)
            results = await indexer.index_all(group="spec")

        assert len(results) == 1
        assert results[0].route.table_name == "sigma_spec"

    @pytest.mark.asyncio
    async def test_index_all_filters_by_group_docs(self, mock_db):
        from dataclasses import dataclass

        from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

        @dataclass
        class FakeResult:
            route: object

        with patch.object(UnifiedIndexer, "index", new_callable=AsyncMock) as mock_index:
            mock_index.return_value = FakeResult(route=ROUTES[0])
            indexer = UnifiedIndexer(db=mock_db)
            results = await indexer.index_all(group="docs")

        assert len(results) == 2
        for r in results:
            assert r.route.table_name == "doc_registry"

    @pytest.mark.asyncio
    async def test_index_all_no_filter_runs_all_routes(self, mock_db):
        from dataclasses import dataclass

        from src.core.pipeline.indexer import ROUTES, UnifiedIndexer

        @dataclass
        class FakeResult:
            route: object

        with patch.object(UnifiedIndexer, "index", new_callable=AsyncMock) as mock_index:
            mock_index.return_value = FakeResult(route=ROUTES[0])
            indexer = UnifiedIndexer(db=mock_db)
            results = await indexer.index_all()

        assert len(results) == 3
