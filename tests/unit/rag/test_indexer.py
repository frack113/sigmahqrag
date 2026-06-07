"""Tests for indexer.py — UnifiedIndexer path resolution and pending fetching."""

from unittest.mock import MagicMock, patch
import pytest

from src.core.pipeline.indexer import UnifiedIndexer, IndexRoute, ROUTES


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def indexer(mock_db):
    return UnifiedIndexer(db=mock_db)


class TestRoutes:
    def test_sigma_spec_route_exists(self):
        route = next((r for r in ROUTES if r.qdrant_collection == "sigma_spec"), None)
        assert route is not None
        assert route.table_name == "sigma_spec"

    def test_sigma_rules_route_exists(self):
        route = next((r for r in ROUTES if r.qdrant_collection == "sigma_rules"), None)
        assert route is not None
        assert route.table_name == "doc_registry"
        assert route.content_type == "sigma_rule"

    def test_sigma_docs_route_exists(self):
        route = next((r for r in ROUTES if r.qdrant_collection == "sigma_docs"), None)
        assert route is not None
        assert route.table_name == "doc_registry"


class TestResolvePath:
    def test_sigma_spec_path(self, indexer):
        with patch("src.core.pipeline.indexer.get_config") as mock_cfg:
            mock_cfg.return_value.paths_sigma_spec_dir = "data/sigma-specification"
            row = {"file_name": "specification/test.md"}
            result = indexer._resolve_path("sigma_spec", row)
            assert result is not None
            assert "sigma-specification" in str(result)
            assert result.name == "test.md"
            assert "specification" in str(result).replace("\\", "/")

    def test_local_org_path(self, indexer):
        with patch("src.core.pipeline.indexer.get_config") as mock_cfg:
            mock_cfg.return_value.local_documents_path = "data/local"
            row = {"org": "local", "repo": "local", "file_name": "test.md"}
            result = indexer._resolve_path("doc_registry", row)
            assert result is not None
            assert "test.md" in str(result)

    def test_sigmaref_org_path(self, indexer):
        with patch("src.core.pipeline.indexer.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = "data/sigmaref"
            row = {"org": "sigmaref", "repo": "sigmaref", "file_name": "test.md"}
            result = indexer._resolve_path("doc_registry", row)
            assert result is not None
            assert "test.md" in str(result)

    def test_github_org_path(self, indexer):
        with patch("src.core.pipeline.indexer.get_config") as mock_cfg:
            mock_cfg.return_value.paths_github_dir = "data/github"
            row = {"org": "SigmaHQ", "repo": "sigma", "file_name": "rules/test.yml"}
            result = indexer._resolve_path("doc_registry", row)
            assert result is not None
            assert "SigmaHQ" in str(result)
            assert "sigma" in str(result)

    def test_empty_org_returns_none(self, indexer):
        row = {"org": "", "repo": "", "file_name": "test.md"}
        result = indexer._resolve_path("doc_registry", row)
        assert result is None


class TestGetPending:
    def test_sigma_spec_delegates_to_db(self, indexer, mock_db):
        mock_db.get_pending_sigma_spec.return_value = [{"url_hash": "abc"}]
        route = IndexRoute("sigma_spec", "sigma_spec")
        result = indexer._get_pending(route)
        mock_db.get_pending_sigma_spec.assert_called_once()
        assert len(result) == 1

    def test_doc_registry_delegates_to_db(self, indexer, mock_db):
        mock_db.get_pending_by_content_type.return_value = [{"url_hash": "def"}]
        route = IndexRoute("doc_registry", "sigma_rules", content_type="sigma_rule")
        result = indexer._get_pending(route)
        mock_db.get_pending_by_content_type.assert_called_once_with("sigma_rule")
        assert len(result) == 1


class TestUpdateStatus:
    def test_sigma_spec_update(self, indexer, mock_db):
        row = {"url_hash": "abc123"}
        indexer._update_status("sigma_spec", row, "embedded")
        mock_db.update_spec_status.assert_called_once_with("abc123", "embedded")

    def test_doc_registry_update(self, indexer, mock_db):
        row = {"url_hash": "def456"}
        indexer._update_status("doc_registry", row, "embedded")
        mock_db.update_doc_registry_embed_status.assert_called_once_with("def456", "embedded")

    def test_missing_hash_skips_update(self, indexer, mock_db):
        row = {}
        indexer._update_status("sigma_spec", row, "embedded")
        mock_db.update_spec_status.assert_not_called()
