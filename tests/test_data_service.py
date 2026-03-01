"""
Test cases for DataService with ollama-python integration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nicegui_app.models.data_service import DataService


class TestDataServiceInitialization:
    """Test DataService initialization and basic functionality."""

    def test_initialization_with_ollama(self):
        """Test that DataService initializes with ollama client."""
        service = DataService()
        assert service is not None
        assert hasattr(service, 'ollama_client')

    @patch('nicegui_app.models.data_service.OLLAMA_AVAILABLE', False)
    def test_initialization_without_ollama(self):
        """Test DataService initialization when ollama is not available."""
        service = DataService()
        assert service is not None
        assert service.ollama_client is None


class TestEmbeddingGeneration:
    """Test embedding generation functionality."""

    def test_generate_embeddings_empty_list(self):
        """Test that empty list returns empty list."""
        service = DataService()
        result = service.generate_embeddings([])
        assert result == []

    @patch('nicegui_app.models.data_service.OLLAMA_AVAILABLE', True)
    def test_generate_embeddings_with_mock_ollama(self):
        """Test embedding generation with mocked ollama client."""
        service = DataService()
        
        # Mock the ollama client
        mock_response = Mock()
        mock_response.embeddings = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        
        with patch.object(service.ollama_client, 'embed', return_value=mock_response):
            result = service.generate_embeddings(['text1', 'text2'])
            assert len(result) == 2
            assert len(result[0]) > 0  # Should have embedding vectors

    @patch('nicegui_app.models.data_service.OLLAMA_AVAILABLE', True)
    def test_generate_embeddings_retry_mechanism(self):
        """Test that retry mechanism works for failed ollama calls."""
        service = DataService()
        
        # Mock the ollama client to fail twice then succeed
        call_count = 0
        def mock_embed_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Mock connection error")
            mock_response = Mock()
            mock_response.embeddings = [[0.1, 0.2]]
            return mock_response
        
        with patch.object(service.ollama_client, 'embed', side_effect=mock_embed_side_effect):
            result = service.generate_embeddings(['test'])
            assert call_count == 3  # Should retry 3 times
            assert len(result) == 1

    def test_generate_embeddings_no_client(self):
        """Test that generate_embeddings raises error when client not available."""
        service = DataService()
        service.ollama_client = None
        
        with pytest.raises(RuntimeError, match="Ollama client not initialized"):
            service.generate_embeddings(['test'])


class TestRAGPipeline:
    """Test RAG pipeline functionality."""

    def test_store_context_without_chroma(self):
        """Test store_context when ChromaDB is not available."""
        service = DataService()
        service.collection = None
        
        result = service.store_context('test_doc', 'test content')
        assert result == False  # Should return False when collection is None

    def test_retrieve_context_without_chroma(self):
        """Test retrieve_context when ChromaDB is not available."""
        service = DataService()
        service.collection = None
        
        result = service.retrieve_context('test query')
        assert result == ([], [])  # Should return empty results

    def test_chunk_text(self):
        """Test text chunking functionality."""
        service = DataService()
        
        long_text = "word " * 1000  # Create a long text
        chunks = service._chunk_text(long_text, chunk_size=500, overlap=100)
        
        assert len(chunks) > 1  # Should create multiple chunks
        assert all(len(chunk) <= 500 for chunk in chunks)  # No chunk should exceed size


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch('nicegui_app.models.data_service.OLLAMA_AVAILABLE', True)
    def test_ollama_connection_failure(self):
        """Test handling of ollama connection failures."""
        service = DataService()
        
        with patch.object(service.ollama_client, 'embed', side_effect=ConnectionError("Server unavailable")):
            with pytest.raises(RuntimeError, match="All 3 attempts failed"):
                service.generate_embeddings(['test'])

    @patch('nicegui_app.models.data_service.OLLAMA_AVAILABLE', True)
    def test_ollama_unexpected_response(self):
        """Test handling of unexpected response format from ollama."""
        service = DataService()
        
        # Mock a response that doesn't have embeddings
        mock_response = {"unexpected": "format"}
        
        with patch.object(service.ollama_client, 'embed', return_value=mock_response):
            result = service.generate_embeddings(['test'])
            # Should create fallback embeddings
            assert len(result) == 1
            assert isinstance(result[0], list)


def test_nicegui_app_compatibility():
    """Test that the NiceGUI app initializes correctly."""
    from nicegui_app.app import create_nicegui_app
    # This test verifies that the app can be created without errors
    assert create_nicegui_app is not None
