"""
Integration tests for component interactions.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.application.app import SigmaHQGradioApp
from src.components.chat_interface import ChatInterface
from src.components.data_management import DataManagement
from src.components.github_management import GitHubManagement
from src.components.file_management import FileManagement
from src.components.config_management import ConfigManagement
from src.components.logs_viewer import LogsViewer


class TestGradioAppIntegration:
    """Integration tests for the main Gradio application."""
    
    @pytest.fixture
    def gradio_app(self, mock_config_service, mock_data_service, mock_logging_service):
        """Create a Gradio app instance for testing."""
        with patch('src.application.app.ConfigService', return_value=mock_config_service), \
             patch('src.application.app.DataService', return_value=mock_data_service), \
             patch('src.application.app.get_logger', return_value=mock_logging_service.get_logger("test")), \
             patch('src.application.app.get_chat_history_service', return_value=Mock()), \
             patch('src.application.app.create_rag_service', return_value=Mock()), \
             patch('src.application.app.create_chat_service', return_value=Mock()):
            
            app = SigmaHQGradioApp()
            yield app
    
    def test_app_initialization(self, gradio_app):
        """Test that the Gradio app initializes correctly."""
        assert gradio_app.config_service is not None
        assert gradio_app.data_service is not None
        assert gradio_app.chat_history_service is not None
        assert gradio_app.rag_chat_service is not None
        assert gradio_app.chat_interface is not None
        assert gradio_app.data_management is not None
        assert gradio_app.github_management is not None
        assert gradio_app.file_management is not None
        assert gradio_app.config_management is not None
        assert gradio_app.logs_viewer is not None
    
    def test_create_interface(self, gradio_app):
        """Test that the interface can be created."""
        interface = gradio_app.create_interface()
        
        assert interface is not None
        assert hasattr(interface, 'launch')
    
    @pytest.mark.asyncio
    async def test_app_lifecycle(self, gradio_app):
        """Test the complete app lifecycle."""
        # Test initialization
        assert gradio_app.app is None
        
        # Test interface creation
        interface = gradio_app.create_interface()
        assert interface is not None
        
        # Test cleanup
        gradio_app.cleanup()
        # Should not raise any exceptions


class TestComponentIntegration:
    """Integration tests for component interactions."""
    
    @pytest.fixture
    def chat_interface(self, mock_chat_service, mock_chat_history_service):
        """Create a chat interface for testing."""
        return ChatInterface(mock_chat_service, mock_chat_history_service)
    
    @pytest.fixture
    def data_management(self, mock_data_service, mock_config_service):
        """Create a data management component for testing."""
        return DataManagement(mock_data_service, mock_config_service)
    
    @pytest.fixture
    def config_management(self, mock_config_service):
        """Create a config management component for testing."""
        return ConfigManagement(mock_config_service)
    
    @pytest.mark.asyncio
    async def test_chat_data_integration(self, chat_interface, data_management, sample_text_file):
        """Test integration between chat and data management."""
        # Process a document through data management
        with patch.object(data_management.data_service, 'process_document', 
                         return_value={"status": "success", "file_path": str(sample_text_file)}):
            result = await data_management._process_documents([sample_text_file])
        
        assert "successfully processed" in result
        
        # The document should now be available for RAG queries
        # (This would be tested more thoroughly in end-to-end tests)
    
    def test_config_data_integration(self, config_management, data_management):
        """Test integration between config and data management."""
        # Update config through config management
        new_config = {"rag": {"enabled": False}}
        config_management.config_service.update_config(new_config)
        
        # Data management should be able to access the updated config
        config = data_management.config_service.get_config()
        assert config["rag"]["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_chat_history_integration(self, chat_interface, mock_chat_history_service):
        """Test integration between chat interface and chat history."""
        # Add a message through chat interface
        await chat_interface._handle_chat_request("Test question", [])
        
        # Chat history service should have recorded the interaction
        # (This would be tested more thoroughly with real services)
        mock_chat_history_service.add_message.assert_called()


class TestServiceIntegration:
    """Integration tests for service interactions."""
    
    @pytest.mark.asyncio
    async def test_llm_rag_integration(self, mock_llm_service, mock_rag_service):
        """Test integration between LLM and RAG services."""
        from src.core.chat_service import ChatService
        
        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            conversation_history_limit=10
        )
        
        # Mock RAG service as initialized
        mock_rag_service.is_initialized = True
        mock_rag_service.query = AsyncMock(return_value=[
            {"text": "Relevant content", "score": 0.9, "metadata": {}}
        ])
        
        # Mock LLM service response
        mock_llm_service.generate_completion = AsyncMock(return_value="LLM response")
        
        # Test chat with RAG
        result = await chat_service.chat("Test question")
        
        assert result == "LLM response"
        mock_rag_service.query.assert_called_once()
        mock_llm_service.generate_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_file_processor_integration(self, mock_data_service, sample_text_file):
        """Test integration between data service and file processor."""
        from src.models.file_processor import FileProcessor
        
        file_processor = FileProcessor()
        
        # Process file with file processor
        text = file_processor.extract_text_from_text(str(sample_text_file))
        chunks = file_processor.chunk_text(text, chunk_size=100, chunk_overlap=20)
        
        # Data service should be able to handle the processed content
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_config_logging_integration(self, mock_config_service, mock_logging_service):
        """Test integration between config and logging services."""
        # Update config
        new_config = {"logging": {"level": "DEBUG"}}
        mock_config_service.update_config(new_config)
        
        # Logging service should be able to access updated config
        logger = mock_logging_service.get_logger("test")
        assert logger is not None
        
        # Both services should work together without conflicts
        config = mock_config_service.get_config()
        assert "logging" in config


class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    @pytest.mark.asyncio
    async def test_llm_service_failure_handling(self, mock_llm_service):
        """Test handling of LLM service failures."""
        from src.core.chat_service import ChatService
        
        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=Mock(),
            conversation_history_limit=10
        )
        
        # Mock LLM service failure
        mock_llm_service.generate_completion = AsyncMock(side_effect=Exception("LLM Error"))
        
        # Should handle the error gracefully
        result = await chat_service.chat("Test question")
        
        assert "Error" in result or "error" in result.lower()
    
    @pytest.mark.asyncio
    async def test_rag_service_failure_handling(self, mock_rag_service):
        """Test handling of RAG service failures."""
        from src.core.chat_service import ChatService
        
        chat_service = ChatService(
            llm_service=Mock(),
            rag_service=mock_rag_service,
            conversation_history_limit=10
        )
        
        # Mock RAG service failure
        mock_rag_service.is_initialized = True
        mock_rag_service.query = AsyncMock(side_effect=Exception("RAG Error"))
        mock_rag_service.is_initialized = False  # Fallback to non-RAG mode
        
        # Should fall back to non-RAG mode
        mock_llm_service = Mock()
        mock_llm_service.generate_completion = AsyncMock(return_value="Fallback response")
        chat_service.llm_service = mock_llm_service
        
        result = await chat_service.chat("Test question")
        
        assert result == "Fallback response"
    
    def test_config_service_failure_handling(self, temp_dir):
        """Test handling of config service failures."""
        from src.models.config_service import ConfigService
        
        config_service = ConfigService(config_path=str(temp_dir / "nonexistent" / "config.json"))
        
        # Should handle missing config file gracefully
        config = config_service.get_config_with_defaults()
        
        assert isinstance(config, dict)
        assert "server" in config
        assert "rag" in config


class TestPerformanceIntegration:
    """Integration tests for performance and scalability."""
    
    @pytest.mark.asyncio
    async def test_concurrent_document_processing(self, mock_data_service, temp_dir):
        """Test concurrent document processing."""
        import asyncio
        from src.models.data_service import DataService
        
        data_service = DataService(data_dir=str(temp_dir))
        
        # Create multiple test files
        test_files = []
        for i in range(5):
            test_file = temp_dir / f"test_{i}.txt"
            test_file.write_text(f"Test content {i}" * 100)
            test_files.append(test_file)
        
        # Process files concurrently
        tasks = [data_service.process_document(str(f)) for f in test_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tasks should complete successfully
        assert len(results) == 5
        assert all(isinstance(result, dict) for result in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_chat_requests(self, mock_chat_service):
        """Test handling concurrent chat requests."""
        import asyncio
        
        # Mock chat service to simulate processing time
        async def mock_chat(message):
            await asyncio.sleep(0.1)  # Simulate processing time
            return f"Response to: {message}"
        
        mock_chat_service.chat = AsyncMock(side_effect=mock_chat)
        
        # Send multiple concurrent requests
        messages = [f"Message {i}" for i in range(5)]
        tasks = [mock_chat_service.chat(msg) for msg in messages]
        results = await asyncio.gather(*tasks)
        
        # All requests should be handled
        assert len(results) == 5
        assert all(f"Response to: Message {i}" in result for i, result in enumerate(results))


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, temp_dir):
        """Test a complete workflow from document upload to chat."""
        # This would be a comprehensive test that:
        # 1. Processes a document
        # 2. Adds it to the RAG system
        # 3. Queries the system
        # 4. Returns a response
        
        # For now, we'll test the individual steps that would be involved
        from src.models.data_service import DataService
        from src.models.file_processor import FileProcessor
        
        # Create test document
        test_file = temp_dir / "e2e_test.txt"
        test_file.write_text("This is test content for end-to-end testing.")
        
        # Process document
        data_service = DataService(data_dir=str(temp_dir))
        file_processor = FileProcessor()
        
        # Extract and chunk text
        text = file_processor.extract_text_from_text(str(test_file))
        chunks = file_processor.chunk_text(text, chunk_size=50, chunk_overlap=10)
        
        # Process through data service
        result = await data_service.process_document(str(test_file))
        
        # Verify the workflow completed
        assert result["status"] == "success"
        assert len(chunks) > 0
        assert "file_path" in result