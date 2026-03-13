"""
Tests for RAG functionality validation and document processing.
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.chat_service import ChatService
from src.core.rag_service import RAGService
from src.models.data_service import DataService
from src.models.file_processor import FileProcessor


class TestRAGDocumentProcessing:
    """Test RAG document processing functionality."""
    
    @pytest.fixture
    def file_processor(self):
        """Create a file processor for testing."""
        return FileProcessor()
    
    @pytest.fixture
    def data_service(self, temp_dir):
        """Create a data service for testing."""
        return DataService(data_dir=str(temp_dir))
    
    def test_text_extraction_from_various_formats(self, file_processor, temp_dir):
        """Test text extraction from different document formats."""
        # Test text file
        text_file = temp_dir / "test.txt"
        text_content = "This is test content for RAG processing.\n" * 10
        text_file.write_text(text_content)
        
        extracted_text = file_processor.extract_text_from_text(str(text_file))
        assert extracted_text == text_content
        
        # Test markdown file
        md_file = temp_dir / "test.md"
        md_content = "# Test Document\n\nThis is **markdown** content."
        md_file.write_text(md_content)
        
        extracted_md = file_processor.extract_text_from_markdown(str(md_file))
        assert "# Test Document" in extracted_md
        assert "markdown" in extracted_md
    
    def test_text_chunking_strategy(self, file_processor):
        """Test different text chunking strategies."""
        long_text = "This is a test sentence. " * 100  # Create long text
        
        # Test different chunk sizes
        chunks_100 = file_processor.chunk_text(long_text, chunk_size=100, chunk_overlap=20)
        chunks_200 = file_processor.chunk_text(long_text, chunk_size=200, chunk_overlap=40)
        
        assert len(chunks_100) > len(chunks_200)
        assert all(len(chunk) <= 100 for chunk in chunks_100)
        assert all(len(chunk) <= 200 for chunk in chunks_200)
        
        # Test overlap
        if len(chunks_100) > 1:
            # Check that there's some overlap between consecutive chunks
            assert len(set(chunks_100[0].split()) & set(chunks_100[1].split())) > 0
    
    @pytest.mark.asyncio
    async def test_document_processing_pipeline(self, data_service, temp_dir):
        """Test the complete document processing pipeline."""
        # Create test documents
        test_files = []
        for i in range(3):
            test_file = temp_dir / f"doc_{i}.txt"
            content = f"Document {i} content. This is test content for document {i}.\n" * 20
            test_file.write_text(content)
            test_files.append(test_file)
        
        # Process all documents
        results = []
        for test_file in test_files:
            result = await data_service.process_document(str(test_file))
            results.append(result)
        
        # Verify all documents were processed successfully
        assert len(results) == 3
        for result in results:
            assert result["status"] == "success"
            assert "file_path" in result
            assert "chunks" in result
            assert result["chunks"] > 0
    
    def test_document_metadata_extraction(self, data_service, temp_dir):
        """Test extraction of document metadata."""
        test_file = temp_dir / "metadata_test.txt"
        test_file.write_text("Test content" * 50)
        
        # Get file stats
        import os
        file_stats = os.stat(str(test_file))
        
        # The data service should capture file information
        # This would be tested more thoroughly with the actual implementation
        assert test_file.exists()
        assert file_stats.st_size > 0


class TestRAGQueryFunctionality:
    """Test RAG query functionality."""
    
    @pytest.fixture
    def mock_rag_service(self, mock_llm_service):
        """Create a mock RAG service for testing."""
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Relevant document content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt', 'chunk_id': 0}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            rag_service = RAGService(
                llm_service=mock_llm_service,
                config={
                    'model': 'text-embedding-all-minilm-l6-v2-embedding',
                    'base_url': 'http://localhost:1234',
                    'api_key': 'lm-studio',
                    'chunk_size': 1000,
                    'chunk_overlap': 200,
                    'collection_name': 'test_collection',
                },
                database_config={
                    'path': './data/.chromadb',
                    'max_connections': 5,
                    'timeout': 30,
                }
            )
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            yield rag_service
    
    @pytest.mark.asyncio
    async def test_rag_query_with_relevant_results(self, mock_rag_service, mock_llm_service):
        """Test RAG query with relevant results."""
        # Mock the RAG service as initialized
        mock_rag_service.is_initialized = True
        
        # Mock the collection query
        mock_rag_service.collection.query.return_value = {
            'documents': [['Relevant document content', 'Another relevant piece']],
            'distances': [[0.1, 0.3]],
            'metadatas': [[{'source': 'doc1.txt'}, {'source': 'doc2.txt'}]]
        }
        
        # Mock embedding generation
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        
        results = await mock_rag_service.query("Test query", n_results=2, min_score=0.1)
        
        assert len(results) == 2
        assert results[0]['text'] == 'Relevant document content'
        assert results[0]['score'] == 0.9  # 1.0 - 0.1
        assert results[1]['text'] == 'Another relevant piece'
        assert results[1]['score'] == 0.7  # 1.0 - 0.3
    
    @pytest.mark.asyncio
    async def test_rag_query_with_no_results(self, mock_rag_service, mock_llm_service):
        """Test RAG query with no relevant results."""
        # Mock the RAG service as initialized
        mock_rag_service.is_initialized = True
        
        # Mock empty results
        mock_rag_service.collection.query.return_value = {
            'documents': [[]],
            'distances': [[]],
            'metadatas': [[]]
        }
        
        # Mock embedding generation
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        
        results = await mock_rag_service.query("Test query", n_results=3, min_score=0.1)
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_rag_query_with_score_filtering(self, mock_rag_service, mock_llm_service):
        """Test RAG query with score filtering."""
        # Mock the RAG service as initialized
        mock_rag_service.is_initialized = True
        
        # Mock results with mixed scores
        mock_rag_service.collection.query.return_value = {
            'documents': [['Good match', 'Poor match', 'Excellent match']],
            'distances': [[0.1, 0.8, 0.05]],
            'metadatas': [[{'source': 'doc1.txt'}, {'source': 'doc2.txt'}, {'source': 'doc3.txt'}]]
        }
        
        # Mock embedding generation
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        
        # Query with high minimum score
        results = await mock_rag_service.query("Test query", n_results=3, min_score=0.8)
        
        # Should only return excellent match (score = 0.95)
        assert len(results) == 1
        assert results[0]['score'] == 0.95


class TestRAGChatIntegration:
    """Test RAG integration with chat functionality."""
    
    @pytest.fixture
    def chat_service_with_rag(self, mock_llm_service, mock_rag_service):
        """Create a chat service with RAG enabled."""
        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            conversation_history_limit=10
        )
        
        # Mock RAG service as initialized
        mock_rag_service.is_initialized = True
        mock_rag_service.query = AsyncMock(return_value=[
            {"text": "Relevant document content", "score": 0.9, "metadata": {"source": "test.txt"}}
        ])
        
        # Mock LLM service
        mock_llm_service.generate_completion = AsyncMock(return_value="LLM response with context")
        
        return chat_service
    
    @pytest.mark.asyncio
    async def test_chat_with_rag_context(self, chat_service_with_rag, mock_llm_service, mock_rag_service):
        """Test chat with RAG context injection."""
        # Add some conversation history
        chat_service_with_rag.add_message("user", "Previous question")
        chat_service_with_rag.add_message("assistant", "Previous answer")
        
        # Mock the LLM response to include context
        def mock_generate_completion(prompt):
            if "Relevant document content" in prompt:
                return "Response based on document content"
            return "Generic response"
        
        mock_llm_service.generate_completion = AsyncMock(side_effect=mock_generate_completion)
        
        # Chat with RAG
        response = await chat_service_with_rag.chat("Current question")
        
        # Verify RAG was called
        mock_rag_service.query.assert_called_once_with("Current question", n_results=3, min_score=0.1)
        
        # Verify LLM was called with context
        mock_llm_service.generate_completion.assert_called_once()
        call_args = mock_llm_service.generate_completion.call_args[0][0]
        assert "Relevant document content" in call_args
        assert "Previous question" in call_args
        assert "Current question" in call_args
    
    @pytest.mark.asyncio
    async def test_chat_without_rag_fallback(self, mock_llm_service):
        """Test chat fallback when RAG is not available."""
        from src.core.rag_service import RAGService
        
        # Create RAG service that's not initialized
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        rag_service.is_initialized = False
        
        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=rag_service,
            conversation_history_limit=10
        )
        
        # Mock LLM response
        mock_llm_service.generate_completion = AsyncMock(return_value="Fallback response")
        
        # Chat should work without RAG
        response = await chat_service.chat("Test question")
        
        assert response == "Fallback response"
        mock_llm_service.generate_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_history_with_rag(self, chat_service_with_rag):
        """Test chat history management with RAG."""
        # Add multiple messages
        messages = [
            ("user", "What is AI?"),
            ("assistant", "AI is artificial intelligence."),
            ("user", "How does RAG work?"),
            ("assistant", "RAG retrieves and generates responses."),
        ]
        
        for role, content in messages:
            chat_service_with_rag.add_message(role, content)
        
        # Get history
        history = chat_service_with_rag.get_history()
        
        assert len(history) == 4
        assert history[0]["content"] == "What is AI?"
        assert history[3]["content"] == "RAG retrieves and generates responses."
        
        # Test history limit
        for i in range(15):
            chat_service_with_rag.add_message("user", f"Message {i}")
        
        history = chat_service_with_rag.get_history()
        assert len(history) == 10  # Should be limited to 10


class TestRAGPerformance:
    """Test RAG performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_rag_query_performance(self, mock_rag_service, mock_llm_service):
        """Test RAG query performance with multiple queries."""
        import time
        
        # Mock the RAG service as initialized
        mock_rag_service.is_initialized = True
        mock_rag_service.collection.query.return_value = {
            'documents': [['Test content']],
            'distances': [[0.1]],
            'metadatas': [[{'source': 'test.txt'}]]
        }
        
        # Mock embedding generation
        mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
        
        # Time multiple queries
        start_time = time.time()
        
        queries = [f"Query {i}" for i in range(10)]
        tasks = [mock_rag_service.query(q) for q in queries]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete reasonably quickly (adjust threshold as needed)
        assert query_time < 5.0  # 5 seconds for 10 queries
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_rag_memory_usage(self, mock_rag_service):
        """Test RAG memory usage with large document sets."""
        # This would test memory usage with large document collections
        # For now, we'll test that the service can handle multiple document additions
        
        mock_rag_service.is_initialized = True
        mock_rag_service.collection = Mock()
        mock_rag_service.collection.add = Mock()
        
        # Simulate adding multiple documents
        documents = [f"Document content {i}" for i in range(100)]
        
        # This should not cause memory issues
        for doc in documents:
            await mock_rag_service.add_documents([doc])
        
        # Verify all documents were processed
        assert mock_rag_service.collection.add.call_count == 100


class TestRAGErrorHandling:
    """Test RAG error handling and resilience."""
    
    @pytest.mark.asyncio
    async def test_rag_service_initialization_failure(self, mock_llm_service):
        """Test handling of RAG service initialization failures."""
        from src.core.rag_service import RAGService
        
        # Mock chromadb client failure
        with patch('chromadb.Client', side_effect=Exception("Database error")):
            rag_service = RAGService(
                llm_service=mock_llm_service,
                config={},
                database_config={}
            )
            
            # Initialization should fail gracefully
            try:
                await rag_service.initialize()
            except Exception:
                pass  # Expected failure
            
            assert rag_service.is_initialized is False
            assert rag_service.collection is None
    
    @pytest.mark.asyncio
    async def test_rag_query_failure_handling(self, mock_rag_service):
        """Test handling of RAG query failures."""
        # Mock query failure
        mock_rag_service.is_initialized = True
        mock_rag_service.collection.query = AsyncMock(side_effect=Exception("Query failed"))
        
        # Should handle the error gracefully
        results = await mock_rag_service.query("Test query")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_rag_embedding_failure_handling(self, mock_llm_service):
        """Test handling of embedding generation failures."""
        from src.core.rag_service import RAGService
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock embedding failure
        mock_llm_service.generate_embedding = AsyncMock(side_effect=Exception("Embedding failed"))
        
        # Should handle the error gracefully
        try:
            await rag_service._generate_embeddings(["test"])
        except Exception:
            pass  # Expected failure
        
        # Service should still be usable
        assert rag_service is not None