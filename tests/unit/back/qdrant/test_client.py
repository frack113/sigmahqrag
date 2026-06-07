"""Tests for Qdrant client factory."""

from __future__ import annotations

from unittest.mock import patch

import src.infrastructure.vectorstore.client as qdrant_module


class TestGetQdrantClient:
    def test_custom_params_create_new(self) -> None:
        with patch.object(qdrant_module, "qdrant_client") as mock_qdrant:
            client = qdrant_module.get_qdrant_client(host="localhost", port=6333, timeout=10.0)
            mock_qdrant.QdrantClient.assert_called_once_with(
                host="localhost", port=6333, timeout=10.0
            )
            assert client is mock_qdrant.QdrantClient.return_value

    def test_custom_params_without_timeout(self) -> None:
        with patch.object(qdrant_module, "qdrant_client") as mock_qdrant:
            client = qdrant_module.get_qdrant_client(host="custom", port=7000)
            mock_qdrant.QdrantClient.assert_called_once_with(host="custom", port=7000)
            assert client is mock_qdrant.QdrantClient.return_value

    def test_custom_params_only_host(self) -> None:
        with patch.object(qdrant_module, "qdrant_client") as mock_qdrant:
            client = qdrant_module.get_qdrant_client(host="remote")
            mock_qdrant.QdrantClient.assert_called_once()
            assert client is mock_qdrant.QdrantClient.return_value

    def test_custom_params_only_port(self) -> None:
        with patch.object(qdrant_module, "qdrant_client") as mock_qdrant:
            client = qdrant_module.get_qdrant_client(port=9999)
            mock_qdrant.QdrantClient.assert_called_once()
            assert client is mock_qdrant.QdrantClient.return_value

    def test_singleton_first_call(self) -> None:
        with (
            patch.object(qdrant_module, "qdrant_client") as mock_qdrant,
            patch("src.config.settings.get_config") as mock_cfg,
            patch.object(qdrant_module, "_client_instance", None),
        ):
            mock_cfg.return_value.qdrant_host = "default"
            mock_cfg.return_value.qdrant_port = 6333
            client = qdrant_module.get_qdrant_client()
            mock_qdrant.QdrantClient.assert_called_once_with(host="default", port=6333)
            assert client is mock_qdrant.QdrantClient.return_value

    def test_singleton_cached(self) -> None:
        fake_client = object()
        with patch.object(qdrant_module, "_client_instance", fake_client):
            client = qdrant_module.get_qdrant_client()
            assert client is fake_client
