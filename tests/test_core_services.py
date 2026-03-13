"""
Unit tests for core services (LLM, RAG, Chat).
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.core.chat_service import ChatService
from src.core.llm_service import LLMService
from src.core.rag_service import RAGService


class TestLLMService:
    """Test cases for LLMService."""

    @pytest.fixture
    def llm_service(self):
        """Create an LLM service instance for testing."""
        return LLMService()

    @pytest.mark.asyncio
    async def test_generate_completion_success(self, llm_service, mock_environment):
        """Test successful completion generation."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(
                return_value={"choices": [{"message": {"content": "Test response"}}]}
            )
            mock_response.raise_for_status = Mock()
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await llm_service.generate_completion("Test prompt")

            assert result == "Test response"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_completion_timeout(self, llm_service, mock_environment):
        """Test completion generation with timeout."""
        with patch("aiohttp.ClientSession.post", side_effect=asyncio.TimeoutError()):
            result = await llm_service.generate_completion("Test prompt")

            assert result == "Error: Request timed out"

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, llm_service, mock_environment):
        """Test successful embedding generation."""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(
                return_value={"data": [{"embedding": [0.1] * 384}]}
            )
            mock_response.raise_for_status = Mock()
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await llm_service.generate_embedding("Test text")

            assert len(result) == 384
            assert all(isinstance(x, float) for x in result)
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_available_true(self, llm_service, mock_environment):
        """Test service availability check when service is available."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await llm_service.is_available()

            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_false(self, llm_service, mock_environment):
        """Test service availability check when service is unavailable."""
        with patch(
            "aiohttp.ClientSession.get", side_effect=Exception("Service unavailable")
        ):
            result = await llm_service.is_available()

            assert result is False


class TestRAGService:
    """Test cases for RAGService."""

    @pytest.fixture
    def rag_service(self, mock_llm_service):
        """Create a RAG service instance for testing."""
        return RAGService(
            llm_service=mock_llm_service,
            config={
                "model": "text-embedding-all-minilm-l6-v2-embedding",
                "base_url": "http://localhost:1234",
                "api_key": "lm-studio",
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "collection_name": "test_collection",
            },
            database_config={
                "path": "./data/.chromadb",
                "max_connections": 5,
                "timeout": 30,
            },
        )

    @pytest.mark.asyncio
    async def test_initialize_success(self, rag_service, mock_llm_service):
        """Test successful RAG service initialization."""
        with patch("chromadb.Client") as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            await rag_service.initialize()

            assert rag_service.is_initialized is True
            assert rag_service.collection is not None

    @pytest.mark.asyncio
    async def test_add_documents_success(
        self, rag_service, sample_text_file, mock_llm_service
    ):
        """Test successful document addition."""
        with patch("chromadb.Client") as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.add = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            await rag_service.initialize()

            # Mock the embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)

            result = await rag_service.add_documents([str(sample_text_file)])

            assert result is True
            mock_collection.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_success(self, rag_service, mock_llm_service):
        """Test successful RAG query."""
        with patch("chromadb.Client") as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "documents": [["Test document content"]],
                "distances": [[0.1]],
                "metadatas": [[{"source": "test.txt"}]],
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            await rag_service.initialize()

            # Mock the embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)

            result = await rag_service.query("Test query")

            assert len(result) == 1
            assert result[0]["text"] == "Test document content"
            assert result[0]["score"] == 0.9  # 1.0 - 0.1

    @pytest.mark.asyncio
    async def test_query_no_results(self, rag_service, mock_llm_service):
        """Test RAG query with no results."""
        with patch("chromadb.Client") as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "documents": [[]],
                "distances": [[]],
                "metadatas": [[]],
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            await rag_service.initialize()

            # Mock the embedding generation
            mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)

            result = await rag_service.query("Test query")

            assert result == []

    @pytest.mark.asyncio
    async def test_cleanup(self, rag_service):
        """Test RAG service cleanup."""
        with patch("chromadb.Client") as mock_chroma:
            mock_client = Mock()
            mock_chroma.return_value = mock_client

            await rag_service.initialize()
            rag_service.cleanup()

            # Verify that the client was properly closed
            assert rag_service.collection is None
            assert rag_service.is_initialized is False


class TestChatService:
    """Test cases for ChatService."""

    @pytest.fixture
    def chat_service(self, mock_llm_service, mock_rag_service):
        """Create a chat service instance for testing."""
        return ChatService(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service,
            conversation_history_limit=10,
        )

    @pytest.mark.asyncio
    async def test_chat_without_rag(
        self, chat_service, mock_llm_service, mock_rag_service
    ):
        """Test chat without RAG enabled."""
        mock_rag_service.is_initialized = False

        result = await chat_service.chat("Test message")

        assert result == "Test response"
        mock_llm_service.generate_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_with_rag(
        self, chat_service, mock_llm_service, mock_rag_service
    ):
        """Test chat with RAG enabled."""
        mock_rag_service.is_initialized = True
        mock_rag_service.query = AsyncMock(
            return_value=[
                {"text": "Relevant document content", "score": 0.9, "metadata": {}}
            ]
        )

        result = await chat_service.chat("Test message")

        assert result == "Test response"
        mock_rag_service.query.assert_called_once_with(
            "Test message", n_results=3, min_score=0.1
        )

    @pytest.mark.asyncio
    async def test_stream_chat(self, chat_service, mock_llm_service, mock_rag_service):
        """Test streaming chat."""
        mock_rag_service.is_initialized = False

        # Mock the streaming response
        async def mock_stream():
            yield "Chunk 1"
            yield "Chunk 2"
            yield "Chunk 3"

        mock_llm_service.stream_completion = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in chat_service.stream_chat("Test message"):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks == ["Chunk 1", "Chunk 2", "Chunk 3"]

    def test_add_message(self, chat_service):
        """Test adding messages to conversation history."""
        chat_service.add_message("user", "Hello")
        chat_service.add_message("assistant", "Hi there")

        history = chat_service.get_history()

        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there"}

    def test_get_history_limit(self, chat_service):
        """Test conversation history limit."""
        # Add more messages than the limit
        for i in range(15):
            chat_service.add_message("user", f"Message {i}")

        history = chat_service.get_history()

        # Should only keep the last 10 messages
        assert len(history) == 10
        assert history[0]["content"] == "Message 5"  # First message within limit

    def test_clear_history(self, chat_service):
        """Test clearing conversation history."""
        chat_service.add_message("user", "Hello")
        chat_service.add_message("assistant", "Hi there")

        chat_service.clear_history()

        history = chat_service.get_history()
        assert len(history) == 0

    def test_get_context_with_history(self, chat_service):
        """Test getting context with conversation history."""
        chat_service.add_message("user", "Previous question")
        chat_service.add_message("assistant", "Previous answer")

        context = chat_service._get_context("Current question")

        assert "Previous question" in context
        assert "Previous answer" in context
        assert "Current question" in context

    def test_get_context_without_history(self, chat_service):
        """Test getting context without conversation history."""
        context = chat_service._get_context("Current question")

        assert "Current question" in context
        assert len(context.split()) == 1  # Only the current question
