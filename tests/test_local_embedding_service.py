"""
Unit tests for LocalEmbeddingService.

These tests run without external dependencies and use mocking to test
the CPU-based embedding functionality.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest
from src.core.local_embedding_service import LocalEmbeddingService


class TestLocalEmbeddingService:
    """Test cases for LocalEmbeddingService."""
    
    @pytest.fixture
    def embedding_config(self):
        """Test configuration for embedding service."""
        return {
            'model': 'all-MiniLM-L6-v2',
            'base_url': 'http://localhost:1234',
            'api_key': 'lm-studio',
            'chunk_size': 1000,
            'chunk_overlap': 200,
        }
    
    @pytest.fixture
    def local_embedding_service(self, embedding_config):
        """Create a local embedding service instance for testing."""
        return LocalEmbeddingService(config=embedding_config)
    
    @pytest.mark.unit
    def test_initialization_success(self, local_embedding_service):
        """Test successful service initialization."""
        assert local_embedding_service.config['model'] == 'all-MiniLM-L6-v2'
        assert local_embedding_service.config['base_url'] == 'http://localhost:1234'
        assert local_embedding_service.config['api_key'] == 'lm-studio'
    
    @pytest.mark.unit
    @patch('src.core.local_embedding_service.SentenceTransformer')
    def test_generate_embeddings_cpu_success(self, mock_sentence_transformer, local_embedding_service):
        """Test successful CPU-based embedding generation."""
        # Mock the sentence transformer model
        mock_model = Mock()
        mock_model.encode = Mock(return_value=[[0.1, 0.2, 0.3]])
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize the service
        local_embedding_service._initialize_model()
        
        # Test embedding generation
        texts = ["Test text"]
        embeddings = asyncio.run(local_embedding_service.generate_embeddings(texts))
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 3
        assert embeddings[0] == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)
    
    @pytest.mark.unit
    @patch('src.core.local_embedding_service.SentenceTransformer')
    def test_generate_embeddings_cpu_empty_input(self, mock_sentence_transformer, local_embedding_service):
        """Test CPU embedding generation with empty input."""
        # Mock the sentence transformer model
        mock_model = Mock()
        mock_model.encode = Mock(return_value=[])
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize the service
        local_embedding_service._initialize_model()
        
        # Test with empty input
        embeddings = asyncio.run(local_embedding_service.generate_embeddings([]))
        
        assert embeddings == []
    
    @pytest.mark.unit
    @patch('src.core.local_embedding_service.SentenceTransformer')
    def test_generate_embeddings_cpu_import_error(self, mock_sentence_transformer, local_embedding_service):
        """Test CPU embedding generation when sentence-transformers is not available."""
        # Mock import error
        mock_sentence_transformer.side_effect = ImportError("sentence-transformers not available")
        
        # Try to initialize the service
        result = local_embedding_service._initialize_model()
        
        assert result is False
        assert local_embedding_service.model is None
    
    @pytest.mark.unit
    @patch('src.core.local_embedding_service.SentenceTransformer')
    def test_generate_embeddings_with_fallback_cpu_success(self, mock_sentence_transformer, local_embedding_service):
        """Test embedding generation with fallback when CPU embeddings succeed."""
        # Mock the sentence transformer model
        mock_model = Mock()
        mock_model.encode = Mock(return_value=[[0.1, 0.2, 0.3]])
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize the service
        local_embedding_service._initialize_model()
        
        # Test embedding generation with fallback
        texts = ["Test text"]
        embeddings = asyncio.run(local_embedding_service.generate_embeddings_with_fallback(texts))
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 3
        assert embeddings[0] == [0.1, 0.2, 0.3]
    
    @pytest.mark.unit
    @patch('src.core.local_embedding_service.SentenceTransformer')
    @patch('requests.post')
    def test_generate_embeddings_with_fallback_api_fallback(self, mock_requests_post, mock_sentence_transformer, local_embedding_service):
        """Test embedding generation with fallback to API when CPU embeddings fail."""
        # Mock CPU embeddings failure
        mock_sentence_transformer.side_effect = ImportError("sentence-transformers not available")
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.4, 0.5, 0.6]}]
        }
        mock_response.raise_for_status = Mock()
        mock_requests_post.return_value = mock_response
        
        # Test embedding generation with fallback
        texts = ["Test text"]
        embeddings = asyncio.run(local_embedding_service.generate_embeddings_with_fallback(texts))
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 3
        assert embeddings[0] == [0.4, 0.5, 0.6]
        mock_requests_post.assert_called_once()
    
    @pytest.mark.unit
    @patch('src.core.local_embedding_service.SentenceTransformer')
    @patch('requests.post')
    def test_generate_embeddings_with_fallback_both_fail(self, mock_requests_post, mock_sentence_transformer, local_embedding_service):
        """Test embedding generation when both CPU and API fail."""
        # Mock CPU embeddings failure
        mock_sentence_transformer.side_effect = ImportError("sentence-transformers not available")
        
        # Mock API failure
        mock_requests_post.side_effect = Exception("API error")
        
        # Test embedding generation with fallback
        texts = ["Test text"]
        
        with pytest.raises(Exception):
            asyncio.run(local_embedding_service.generate_embeddings_with_fallback(texts, use_fallback=True))
    
    @pytest.mark.unit
    def test_get_embedding_stats(self, local_embedding_service):
        """Test getting embedding statistics."""
        stats = local_embedding_service.get_embedding_stats()
        
        assert 'total_embeddings' in stats
        assert 'cpu_embeddings' in stats
        assert 'api_fallbacks' in stats
        assert 'failed_embeddings' in stats
        assert 'success_rate' in stats
        assert 'average_response_time' in stats
        assert 'memory_usage_mb' in stats
        assert 'cpu_usage_percent' in stats
        assert 'last_error' in stats
        assert 'uptime_seconds' in stats
    
    @pytest.mark.unit
    def test_get_health_status(self, local_embedding_service):
        """Test getting service health status."""
        health_status = local_embedding_service.get_health_status()
        
        assert 'service' in health_status
        assert 'status' in health_status
        assert 'issues' in health_status
        assert 'timestamp' in health_status
        assert 'stats' in health_status
    
    @pytest.mark.unit
    def test_update_config(self, local_embedding_service):
        """Test updating service configuration."""
        new_config = {
            'model': 'new-model',
            'base_url': 'http://new:1234',
            'api_key': 'new-key',
            'chunk_size': 2000,
            'chunk_overlap': 400,
        }
        
        result = local_embedding_service.update_config(new_config)
        
        assert result is True
        assert local_embedding_service.config['model'] == 'new-model'
        assert local_embedding_service.config['base_url'] == 'http://new:1234'
        assert local_embedding_service.config['api_key'] == 'new-key'
    
    @pytest.mark.unit
    def test_cleanup(self, local_embedding_service):
        """Test service cleanup."""
        # Initialize the service
        local_embedding_service._initialized = True
        
        # Mock the executor
        local_embedding_service.executor = Mock()
        
        # Call cleanup
        local_embedding_service.cleanup()
        
        # Verify cleanup was called
        assert local_embedding_service._initialized is False
        local_embedding_service.executor.shutdown.assert_called_once_with(wait=True)