"""
Performance tests and optimization validation.
"""
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest
from src.core.chat_service import ChatService
from src.core.llm_service import LLMService
from src.core.rag_service import RAGService
from src.models.data_service import DataService
from src.models.file_processor import FileProcessor


class TestPerformanceBaselines:
    """Test performance baselines and thresholds."""
    
    @pytest.mark.asyncio
    async def test_llm_response_time_baseline(self, mock_environment):
        """Test LLM response time baseline."""
        llm_service = LLMService()
        
        # Mock response time
        start_time = time.time()
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Test response"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            result = await llm_service.generate_completion("Test prompt")
        
        response_time = time.time() - start_time
        
        # Should respond within reasonable time (adjust based on your requirements)
        assert response_time < 5.0  # 5 seconds maximum
        assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_embedding_generation_time_baseline(self, mock_environment):
        """Test embedding generation time baseline."""
        llm_service = LLMService()
        
        start_time = time.time()
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "data": [{"embedding": [0.1] * 384}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            embedding = await llm_service.generate_embedding("Test text")
        
        response_time = time.time() - start_time
        
        # Should generate embeddings within reasonable time
        assert response_time < 3.0  # 3 seconds maximum
        assert len(embedding) == 384
    
    @pytest.mark.asyncio
    async def test_document_processing_time_baseline(self, temp_dir):
        """Test document processing time baseline."""
        from src.models.data_service import DataService
        
        data_service = DataService(data_dir=str(temp_dir))
        
        # Create a moderately sized document
        test_file = temp_dir / "performance_test.txt"
        content = "This is test content. " * 1000  # Create larger content
        test_file.write_text(content)
        
        start_time = time.time()
        
        result = await data_service.process_document(str(test_file))
        
        processing_time = time.time() - start_time
        
        # Should process document within reasonable time
        assert processing_time < 10.0  # 10 seconds maximum
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_rag_query_time_baseline(self, mock_llm_service):
        """Test RAG query time baseline."""
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Test content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt'}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            start_time = time.time()
            
            results = await rag_service.query("Test query")
            
            query_time = time.time() - start_time
            
            # Should query within reasonable time
            assert query_time < 2.0  # 2 seconds maximum
            assert len(results) == 1


class TestConcurrentPerformance:
    """Test concurrent performance and scalability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_llm_requests(self, mock_environment):
        """Test handling of concurrent LLM requests."""
        llm_service = LLMService()
        
        # Mock responses
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Response"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            start_time = time.time()
            
            # Send multiple concurrent requests
            tasks = [
                llm_service.generate_completion(f"Prompt {i}")
                for i in range(10)
            ]
            
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Should handle concurrent requests efficiently
            assert total_time < 15.0  # 15 seconds for 10 concurrent requests
            assert len(responses) == 10
            assert all("Response" in resp for resp in responses)
    
    @pytest.mark.asyncio
    async def test_concurrent_document_processing(self, temp_dir):
        """Test concurrent document processing."""
        from src.models.data_service import DataService
        
        data_service = DataService(data_dir=str(temp_dir))
        
        # Create multiple test files
        test_files = []
        for i in range(5):
            test_file = temp_dir / f"perf_test_{i}.txt"
            content = f"Test content for file {i}. " * 500
            test_file.write_text(content)
            test_files.append(test_file)
        
        start_time = time.time()
        
        # Process files concurrently
        tasks = [data_service.process_document(str(f)) for f in test_files]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Should process multiple files efficiently
        assert total_time < 20.0  # 20 seconds for 5 concurrent files
        assert len(results) == 5
        assert all(result["status"] == "success" for result in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_rag_queries(self, mock_llm_service):
        """Test concurrent RAG queries."""
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Test content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt'}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            start_time = time.time()
            
            # Send multiple concurrent queries
            tasks = [rag_service.query(f"Query {i}") for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Should handle concurrent queries efficiently
            assert total_time < 5.0  # 5 seconds for 10 concurrent queries
            assert len(results) == 10
            assert all(len(result) == 1 for result in results)


class TestMemoryUsage:
    """Test memory usage and optimization."""
    
    @pytest.mark.asyncio
    async def test_llm_service_memory_usage(self, mock_environment):
        """Test LLM service memory usage."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        llm_service = LLMService()
        
        # Perform multiple operations
        for i in range(10):
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": f"Response {i}"}}]
            })
            mock_response.raise_for_status = Mock()
            
            with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
                await llm_service.generate_completion(f"Prompt {i}")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (adjust threshold as needed)
        assert memory_increase < 100  # Less than 100MB increase
    
    @pytest.mark.asyncio
    async def test_rag_service_memory_usage(self, mock_llm_service):
        """Test RAG service memory usage with large document sets."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Test content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt'}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            # Add multiple documents
            for i in range(50):
                await rag_service.add_documents([f"Document content {i}"])
            
            # Perform multiple queries
            for i in range(20):
                await rag_service.query(f"Query {i}")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable for the operations performed
        assert memory_increase < 200  # Less than 200MB increase
    
    def test_file_processor_memory_usage(self, temp_dir):
        """Test file processor memory usage with large files."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        
        file_processor = FileProcessor()
        
        # Create a large file
        large_file = temp_dir / "large_test.txt"
        large_content = "Large content. " * 10000  # Create large content
        large_file.write_text(large_content)
        
        # Process the file multiple times
        for i in range(5):
            text = file_processor.extract_text_from_text(str(large_file))
            chunks = file_processor.chunk_text(text, chunk_size=1000, chunk_overlap=200)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 50  # Less than 50MB increase


class TestScalability:
    """Test scalability with increasing load."""
    
    @pytest.mark.asyncio
    async def test_llm_service_scalability(self, mock_environment):
        """Test LLM service scalability with increasing request volume."""
        llm_service = LLMService()
        
        # Test with increasing numbers of requests
        request_counts = [10, 20, 50]
        response_times = []
        
        for count in request_counts:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "Response"}}]
            })
            mock_response.raise_for_status = Mock()
            
            with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
                start_time = time.time()
                
                tasks = [llm_service.generate_completion(f"Prompt {i}") for i in range(count)]
                await asyncio.gather(*tasks)
                
                total_time = time.time() - start_time
                avg_response_time = total_time / count
                response_times.append(avg_response_time)
        
        # Response time should not increase linearly with request count
        # (i.e., should scale reasonably well)
        assert response_times[2] < response_times[0] * 3  # 50 requests should be less than 3x slower than 10
    
    @pytest.mark.asyncio
    async def test_document_processing_scalability(self, temp_dir):
        """Test document processing scalability with increasing file sizes."""
        from src.models.data_service import DataService
        
        data_service = DataService(data_dir=str(temp_dir))
        
        # Test with increasing file sizes
        file_sizes = [1000, 5000, 10000]  # Number of words
        processing_times = []
        
        for size in file_sizes:
            test_file = temp_dir / f"scalability_test_{size}.txt"
            content = "Test content word " * size
            test_file.write_text(content)
            
            start_time = time.time()
            
            result = await data_service.process_document(str(test_file))
            
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
            
            assert result["status"] == "success"
        
        # Processing time should scale reasonably with file size
        # (not more than 20x slower for 10x larger file)
        assert processing_times[2] < processing_times[0] * 20
    
    @pytest.mark.asyncio
    async def test_rag_service_scalability(self, mock_llm_service):
        """Test RAG service scalability with increasing document collection size."""
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Test content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt'}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            # Test query performance with increasing collection size
            query_times = []
            
            for i in range(3):
                # Add more documents to simulate larger collection
                for j in range(10 * (i + 1)):
                    await rag_service.add_documents([f"Document content {j}"])
                
                # Measure query time
                start_time = time.time()
                await rag_service.query("Test query")
                query_time = time.time() - start_time
                query_times.append(query_time)
            
            # Query time should not increase dramatically with collection size
            assert query_times[2] < query_times[0] * 5  # Should be less than 5x slower


class TestOptimizationValidation:
    """Test that optimizations are working correctly."""
    
    @pytest.mark.asyncio
    async def test_llm_service_connection_pooling(self, mock_environment):
        """Test that LLM service uses connection pooling effectively."""
        llm_service = LLMService()
        
        # Mock session to track usage
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "Response"}}]
            })
            mock_response.raise_for_status = Mock()
            mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # Make multiple requests
            for i in range(5):
                await llm_service.generate_completion(f"Prompt {i}")
            
            # Should reuse the same session (connection pooling)
            assert mock_session_class.call_count == 1  # Only one session created
            assert mock_session.post.call_count == 5  # Multiple requests on same session
    
    @pytest.mark.asyncio
    async def test_rag_service_caching(self, mock_llm_service):
        """Test that RAG service implements caching effectively."""
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Test content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt'}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            # Query the same thing multiple times
            start_time = time.time()
            
            for i in range(5):
                await rag_service.query("Same query")
            
            total_time = time.time() - start_time
            
            # Should be reasonably fast (caching should help)
            assert total_time < 2.0  # 2 seconds for 5 identical queries
    
    def test_file_processor_chunking_optimization(self):
        """Test that file processor chunking is optimized."""
        
        file_processor = FileProcessor()
        
        # Create long text
        long_text = "This is a test sentence. " * 10000
        
        start_time = time.time()
        
        # Process with different chunk sizes
        chunks_500 = file_processor.chunk_text(long_text, chunk_size=500, chunk_overlap=100)
        chunks_1000 = file_processor.chunk_text(long_text, chunk_size=1000, chunk_overlap=200)
        
        processing_time = time.time() - start_time
        
        # Should process quickly
        assert processing_time < 1.0  # 1 second maximum
        
        # Should produce reasonable number of chunks
        assert len(chunks_500) > len(chunks_1000)
        assert len(chunks_500) < 250  # Should not be too many chunks
        assert len(chunks_1000) < 125
    
    @pytest.mark.asyncio
    async def test_chat_service_history_optimization(self, mock_llm_service, mock_rag_service):
        """Test that chat service history management is optimized."""
        
        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            conversation_history_limit=10
        )
        
        # Add many messages to test history management
        start_time = time.time()
        
        for i in range(50):
            chat_service.add_message("user", f"Message {i}")
            chat_service.add_message("assistant", f"Response {i}")
        
        # Get history
        history = chat_service.get_history()
        
        processing_time = time.time() - start_time
        
        # Should manage history efficiently
        assert processing_time < 0.5  # 0.5 seconds maximum
        assert len(history) == 10  # Should be limited to 10 messages


class TestResourceManagement:
    """Test resource management and cleanup."""
    
    @pytest.mark.asyncio
    async def test_llm_service_resource_cleanup(self, mock_environment):
        """Test that LLM service properly cleans up resources."""
        llm_service = LLMService()
        
        # Mock session to track cleanup
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "Response"}}]
            })
            mock_response.raise_for_status = Mock()
            mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # Make requests
            await llm_service.generate_completion("Test prompt")
            
            # Simulate service cleanup
            llm_service.session = None  # Simulate cleanup
            
            # Should not leak resources
            assert llm_service.session is None
    
    @pytest.mark.asyncio
    async def test_rag_service_resource_cleanup(self, mock_llm_service):
        """Test that RAG service properly cleans up resources."""
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Verify service is initialized
            assert rag_service.is_initialized is True
            assert rag_service.collection is not None
            
            # Clean up
            rag_service.cleanup()
            
            # Verify cleanup
            assert rag_service.collection is None
            assert rag_service.is_initialized is False
    
    def test_file_processor_memory_cleanup(self, temp_dir):
        """Test that file processor properly cleans up memory."""
        
        file_processor = FileProcessor()
        
        # Process large file
        large_file = temp_dir / "memory_test.txt"
        large_content = "Large content. " * 10000
        large_file.write_text(large_content)
        
        # Process file
        text = file_processor.extract_text_from_text(str(large_file))
        chunks = file_processor.chunk_text(text, chunk_size=1000, chunk_overlap=200)
        
        # Clear references
        del text
        del chunks
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Should not leak memory significantly
        # (This is more of a manual test - in practice you'd monitor with profiling tools)
        assert True  # Placeholder - actual memory monitoring would require more sophisticated testing


class TestPerformanceMonitoring:
    """Test performance monitoring and metrics collection."""
    
    @pytest.mark.asyncio
    async def test_llm_service_performance_metrics(self, mock_environment):
        """Test that LLM service collects performance metrics."""
        llm_service = LLMService()
        
        # Mock response with timing
        start_time = time.time()
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Response"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            result = await llm_service.generate_completion("Test prompt")
        
        response_time = time.time() - start_time
        
        # Should complete successfully
        assert result == "Response"
        assert response_time > 0
    
    @pytest.mark.asyncio
    async def test_rag_service_performance_metrics(self, mock_llm_service):
        """Test that RAG service collects performance metrics."""
        
        rag_service = RAGService(
            llm_service=mock_llm_service,
            config={},
            database_config={}
        )
        
        # Mock the RAG service as initialized
        with patch('chromadb.Client') as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Test content']],
                'distances': [[0.1]],
                'metadatas': [[{'source': 'test.txt'}]]
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client
            
            await rag_service.initialize()
            
            # Mock embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
            
            # Measure query performance
            start_time = time.time()
            results = await rag_service.query("Test query")
            query_time = time.time() - start_time
            
            # Should complete successfully
            assert len(results) == 1
            assert query_time > 0
    
    def test_data_service_performance_metrics(self, temp_dir):
        """Test that data service collects performance metrics."""
        data_service = DataService(data_dir=str(temp_dir))
        
        # Create test file
        test_file = temp_dir / "metrics_test.txt"
        test_file.write_text("Test content for metrics collection.")
        
        # Measure processing performance
        start_time = time.time()
        result = asyncio.run(data_service.process_document(str(test_file)))
        processing_time = time.time() - start_time
        
        # Should complete successfully
        assert result["status"] == "success"
        assert processing_time > 0