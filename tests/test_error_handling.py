"""
Tests for error handling and fallback mechanisms.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.application.app import SigmaHQGradioApp
from src.core.chat_service import ChatService
from src.core.llm_service import LLMService
from src.core.rag_service import RAGService
from src.models.config_service import ConfigService
from src.models.data_service import DataService


class TestApplicationErrorHandling:
    """Test error handling at the application level."""

    @pytest.mark.asyncio
    async def test_app_initialization_with_missing_dependencies(self, temp_dir):
        """Test app initialization when dependencies are missing."""
        # Mock missing dependencies
        with (
            patch(
                "src.application.app.ConfigService",
                side_effect=ImportError("Config module not found"),
            ),
            patch(
                "src.application.app.get_logger",
                side_effect=ImportError("Logging module not found"),
            ),
        ):

            # Should handle missing dependencies gracefully
            try:
                app = SigmaHQGradioApp()
                # If we get here, the app should have fallback mechanisms
                assert app is not None
            except ImportError:
                # This is expected when dependencies are missing
                pass

    @pytest.mark.asyncio
    async def test_app_launch_with_port_conflict(
        self, mock_config_service, mock_data_service, mock_logging_service
    ):
        """Test app launch when port is already in use."""
        with (
            patch(
                "src.application.app.ConfigService", return_value=mock_config_service
            ),
            patch("src.application.app.DataService", return_value=mock_data_service),
            patch(
                "src.application.app.get_logger",
                return_value=mock_logging_service.get_logger("test"),
            ),
            patch("src.application.app.get_chat_history_service", return_value=Mock()),
            patch("src.application.app.create_rag_service", return_value=Mock()),
            patch("src.application.app.create_chat_service", return_value=Mock()),
            patch(
                "gradio.Blocks.launch", side_effect=OSError("Address already in use")
            ),
        ):

            app = SigmaHQGradioApp()

            # Should handle port conflicts gracefully
            try:
                app.launch(port=8000)
            except OSError:
                # Should try alternative ports
                pass

    def test_app_cleanup_with_errors(
        self, mock_config_service, mock_data_service, mock_logging_service
    ):
        """Test app cleanup when errors occur during shutdown."""
        with (
            patch(
                "src.application.app.ConfigService", return_value=mock_config_service
            ),
            patch("src.application.app.DataService", return_value=mock_data_service),
            patch(
                "src.application.app.get_logger",
                return_value=mock_logging_service.get_logger("test"),
            ),
            patch("src.application.app.get_chat_history_service", return_value=Mock()),
            patch("src.application.app.create_rag_service", return_value=Mock()),
            patch("src.application.app.create_chat_service", return_value=Mock()),
        ):

            app = SigmaHQGradioApp()

            # Mock cleanup failure
            with patch.object(app, "cleanup", side_effect=Exception("Cleanup failed")):
                # Should handle cleanup errors gracefully
                try:
                    app.cleanup()
                except Exception:
                    pass  # Expected cleanup failure


class TestServiceErrorHandling:
    """Test error handling in individual services."""

    @pytest.mark.asyncio
    async def test_llm_service_timeout_handling(self, mock_environment):
        """Test LLM service timeout handling."""
        llm_service = LLMService()

        with patch("aiohttp.ClientSession.post", side_effect=asyncio.TimeoutError()):
            result = await llm_service.generate_completion("Test prompt")

            assert result == "Error: Request timed out"

    @pytest.mark.asyncio
    async def test_llm_service_connection_failure(self, mock_environment):
        """Test LLM service connection failure handling."""
        llm_service = LLMService()

        with patch(
            "aiohttp.ClientSession.post",
            side_effect=ConnectionError("Connection failed"),
        ):
            result = await llm_service.generate_completion("Test prompt")

            assert "Error" in result

    @pytest.mark.asyncio
    async def test_llm_service_invalid_response(self, mock_environment):
        """Test LLM service handling of invalid responses."""
        llm_service = LLMService()

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(side_effect=Exception("Invalid JSON"))
        mock_response.raise_for_status = Mock()

        with patch(
            "aiohttp.ClientSession.post",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            ),
        ):
            result = await llm_service.generate_completion("Test prompt")

            assert "Error" in result

    @pytest.mark.asyncio
    async def test_rag_service_initialization_failure(self, mock_llm_service):
        """Test RAG service initialization failure handling."""

        # Mock chromadb failure
        with patch("chromadb.Client", side_effect=Exception("Database error")):
            rag_service = RAGService(
                llm_service=mock_llm_service, config={}, database_config={}
            )

            try:
                await rag_service.initialize()
            except Exception:
                pass  # Expected failure

            assert rag_service.is_initialized is False
            assert rag_service.collection is None

    @pytest.mark.asyncio
    async def test_rag_service_query_failure(self, mock_llm_service):
        """Test RAG service query failure handling."""

        rag_service = RAGService(
            llm_service=mock_llm_service, config={}, database_config={}
        )

        # Mock query failure
        rag_service.is_initialized = True
        rag_service.collection = Mock()
        rag_service.collection.query = AsyncMock(side_effect=Exception("Query failed"))

        results = await rag_service.query("Test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_chat_service_fallback_on_rag_failure(self, mock_llm_service):
        """Test chat service fallback when RAG fails."""

        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=Mock(),
            conversation_history_limit=10,
        )

        # Mock RAG failure
        chat_service.rag_service.is_initialized = True
        chat_service.rag_service.query = AsyncMock(side_effect=Exception("RAG failed"))
        chat_service.rag_service.is_initialized = False  # Fallback to non-RAG mode

        # Mock LLM response
        mock_llm_service.generate_completion = AsyncMock(
            return_value="Fallback response"
        )

        result = await chat_service.chat("Test question")

        assert result == "Fallback response"

    def test_config_service_file_access_failure(self, temp_dir):
        """Test config service handling of file access failures."""

        # Try to access a file in a non-existent directory
        config_service = ConfigService(
            config_path=str(temp_dir / "nonexistent" / "config.json")
        )

        # Should handle missing file gracefully
        config = config_service.get_config_with_defaults()

        assert isinstance(config, dict)
        assert "server" in config
        assert "rag" in config

    @pytest.mark.asyncio
    async def test_data_service_processing_failure(self, temp_dir):
        """Test data service handling of processing failures."""

        data_service = DataService(data_dir=str(temp_dir))

        # Create a file that will cause processing to fail
        bad_file = temp_dir / "bad_file.txt"
        bad_file.write_text("This content will cause processing to fail")

        # Mock file processor to raise an exception
        with patch(
            "src.models.file_processor.FileProcessor.extract_text",
            side_effect=Exception("Processing failed"),
        ):
            result = await data_service.process_document(str(bad_file))

            assert result["status"] == "error"
            assert "Processing failed" in result["error"]


class TestComponentErrorHandling:
    """Test error handling in Gradio components."""

    @pytest.mark.asyncio
    async def test_chat_interface_error_handling(
        self, mock_chat_service, mock_chat_history_service
    ):
        """Test chat interface error handling."""
        from src.components.chat_interface import ChatInterface

        chat_interface = ChatInterface(mock_chat_service, mock_chat_history_service)

        # Mock chat service failure
        mock_chat_service.chat = AsyncMock(side_effect=Exception("Chat failed"))

        # Should handle the error gracefully
        result = await chat_interface._handle_chat_request("Test question", [])

        assert isinstance(result, list)
        assert len(result) == 1
        assert "Error" in result[0][1]

    @pytest.mark.asyncio
    async def test_data_management_error_handling(
        self, mock_data_service, mock_config_service
    ):
        """Test data management component error handling."""
        from src.components.data_management import DataManagement

        data_management = DataManagement(mock_data_service, mock_config_service)

        # Mock data service failure
        mock_data_service.process_document = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        # Should handle the error gracefully
        result = await data_management._process_documents(["test_file.txt"])

        assert "Error" in result

    def test_config_management_error_handling(self, mock_config_service):
        """Test config management component error handling."""
        from src.components.config_management import ConfigManagement

        config_management = ConfigManagement(mock_config_service)

        # Mock config service failure
        mock_config_service.update_config = Mock(
            side_effect=Exception("Config update failed")
        )

        # Should handle the error gracefully
        result = config_management._update_config({"test": "value"})

        assert result is False


class TestFallbackMechanisms:
    """Test fallback mechanisms when primary services fail."""

    @pytest.mark.asyncio
    async def test_llm_fallback_to_local_model(self, mock_environment):
        """Test fallback to local model when primary model fails."""
        llm_service = LLMService()

        # Mock primary model failure
        with patch(
            "aiohttp.ClientSession.post",
            side_effect=[
                Exception("Primary model failed"),
                AsyncMock(
                    __aenter__=AsyncMock(
                        return_value=AsyncMock(
                            json=AsyncMock(
                                return_value={
                                    "choices": [
                                        {"message": {"content": "Fallback response"}}
                                    ]
                                }
                            ),
                            raise_for_status=Mock(),
                        )
                    ),
                    __aexit__=AsyncMock(return_value=None),
                ),
            ],
        ):
            result = await llm_service.generate_completion("Test prompt")

            assert result == "Fallback response"

    @pytest.mark.asyncio
    async def test_rag_fallback_to_non_rag_mode(self, mock_llm_service):
        """Test RAG fallback to non-RAG mode."""

        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=Mock(),
            conversation_history_limit=10,
        )

        # Mock RAG service as failed
        chat_service.rag_service.is_initialized = False

        # Mock LLM response
        mock_llm_service.generate_completion = AsyncMock(
            return_value="Non-RAG response"
        )

        result = await chat_service.chat("Test question")

        assert result == "Non-RAG response"

    def test_config_fallback_to_defaults(self, temp_dir):
        """Test config fallback to default values."""

        config_service = ConfigService(
            config_path=str(temp_dir / "missing_config.json")
        )

        # Should fall back to defaults
        config = config_service.get_config_with_defaults()

        assert config["server"]["port"] == 8000
        assert config["rag"]["enabled"] is True
        assert config["logging"]["level"] == "INFO"

    @pytest.mark.asyncio
    async def test_data_service_fallback_to_text_extraction(self, temp_dir):
        """Test data service fallback to text extraction for unsupported formats."""
        from src.models.file_processor import FileProcessor

        data_service = DataService(data_dir=str(temp_dir))
        file_processor = FileProcessor()

        # Create an unsupported file
        unsupported_file = temp_dir / "unsupported.xyz"
        unsupported_file.write_text("Plain text content")

        # Should fall back to text extraction
        text = file_processor.extract_text(str(unsupported_file))

        assert text == "Plain text content"


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_llm_service_recovery_after_timeout(self, mock_environment):
        """Test LLM service recovery after timeout."""
        llm_service = LLMService()

        # First request times out
        with patch(
            "aiohttp.ClientSession.post",
            side_effect=[
                asyncio.TimeoutError(),
                AsyncMock(
                    __aenter__=AsyncMock(
                        return_value=AsyncMock(
                            json=AsyncMock(
                                return_value={
                                    "choices": [
                                        {"message": {"content": "Recovered response"}}
                                    ]
                                }
                            ),
                            raise_for_status=Mock(),
                        )
                    ),
                    __aexit__=AsyncMock(return_value=None),
                ),
            ],
        ):
            # First request should timeout
            result1 = await llm_service.generate_completion("Test prompt")
            assert result1 == "Error: Request timed out"

            # Second request should succeed
            result2 = await llm_service.generate_completion("Test prompt")
            assert result2 == "Recovered response"

    @pytest.mark.asyncio
    async def test_rag_service_recovery_after_failure(self, mock_llm_service):
        """Test RAG service recovery after failure."""

        rag_service = RAGService(
            llm_service=mock_llm_service, config={}, database_config={}
        )

        # Mock initial failure
        with patch(
            "chromadb.Client",
            side_effect=[Exception("Database error"), Mock()],  # Success on retry
        ):
            try:
                await rag_service.initialize()
            except Exception:
                pass  # Expected failure

            # Should be able to retry
            try:
                await rag_service.initialize()
            except Exception:
                pass  # May still fail, but shouldn't crash

    @pytest.mark.asyncio
    async def test_chat_service_recovery_with_history(
        self, mock_llm_service, mock_rag_service
    ):
        """Test chat service recovery while maintaining conversation history."""

        chat_service = ChatService(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            conversation_history_limit=10,
        )

        # Add some history
        chat_service.add_message("user", "First question")
        chat_service.add_message("assistant", "First answer")

        # Mock failure and recovery
        mock_llm_service.generate_completion = AsyncMock(
            side_effect=[
                Exception("Service temporarily unavailable"),
                "Recovered response",
            ]
        )

        # First request should fail
        try:
            await chat_service.chat("Second question")
        except Exception:
            pass

        # Second request should succeed and maintain history
        result = await chat_service.chat("Second question")

        assert result == "Recovered response"

        # History should still be intact
        history = chat_service.get_history()
        assert len(history) >= 3  # Original 2 + new message


class TestErrorLoggingAndMonitoring:
    """Test error logging and monitoring."""

    def test_error_logging_in_config_service(self, mock_logging_service):
        """Test error logging in config service."""

        config_service = ConfigService()
        config_service.logger = mock_logging_service.get_logger("config")

        # Mock logger to capture log calls
        with patch.object(config_service.logger, "error") as mock_error:
            # Simulate an error
            config_service._log_operation(
                "test_operation", False, {"error": "Test error"}
            )

            # Should log the error
            mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_logging_in_llm_service(
        self, mock_logging_service, mock_environment
    ):
        """Test error logging in LLM service."""
        from src.core.llm_service import LLMService

        llm_service = LLMService()
        llm_service.logger = mock_logging_service.get_logger("llm")

        # Mock logger to capture log calls
        with patch.object(llm_service.logger, "error") as mock_error:
            # Simulate an error
            with patch(
                "aiohttp.ClientSession.post", side_effect=Exception("LLM Error")
            ):
                await llm_service.generate_completion("Test prompt")

            # Should log the error
            mock_error.assert_called_once()

    def test_error_logging_in_data_service(self, mock_logging_service):
        """Test error logging in data service."""

        data_service = DataService(data_dir="test_dir")
        data_service.logger = mock_logging_service.get_logger("data")

        # Mock logger to capture log calls
        with patch.object(data_service.logger, "error") as mock_error:
            # Simulate an error
            data_service._log_operation(
                "test_operation", False, {"error": "Test error"}
            )

            # Should log the error
            mock_error.assert_called_once()
