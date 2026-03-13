"""
Unit tests for model services.
"""
import asyncio
from unittest.mock import Mock, patch

import pytest
from src.models.chat_history_service import ChatHistoryService
from src.models.config_service import ConfigService
from src.models.data_service import DataService
from src.models.file_processor import FileProcessor
from src.models.logging_service import LoggingService
from src.models.repository_service import RepositoryService


class TestConfigService:
    """Test cases for ConfigService."""
    
    @pytest.fixture
    def config_service(self, temp_dir):
        """Create a config service instance for testing."""
        config_path = temp_dir / "config.json"
        return ConfigService(config_path=str(config_path))
    
    def test_get_config_with_defaults(self, config_service):
        """Test getting config with default values."""
        config = config_service.get_config_with_defaults()
        
        assert "server" in config
        assert "rag" in config
        assert "logging" in config
        assert config["server"]["port"] == 8000
        assert config["rag"]["enabled"] is True
        assert config["logging"]["level"] == "INFO"
    
    def test_update_config(self, config_service):
        """Test updating configuration."""
        new_config = {
            "server": {"port": 9000},
            "rag": {"enabled": False}
        }
        
        result = config_service.update_config(new_config)
        
        assert result is True
        updated_config = config_service.get_config()
        assert updated_config["server"]["port"] == 9000
        assert updated_config["rag"]["enabled"] is False
    
    def test_save_config(self, config_service, temp_dir):
        """Test saving configuration to file."""
        config = {"test": "value"}
        config_path = temp_dir / "test_config.json"
        
        result = config_service.save_config(config, str(config_path))
        
        assert result is True
        assert config_path.exists()
        
        # Verify the saved content
        saved_config = config_service.load_config(str(config_path))
        assert saved_config == config
    
    def test_load_config_nonexistent(self, config_service):
        """Test loading config from nonexistent file."""
        result = config_service.load_config("nonexistent.json")
        assert result == {}


class TestDataService:
    """Test cases for DataService."""
    
    @pytest.fixture
    def data_service(self, temp_dir):
        """Create a data service instance for testing."""
        return DataService(data_dir=str(temp_dir))
    
    @pytest.mark.asyncio
    async def test_process_document_text(self, data_service, sample_text_file):
        """Test processing a text document."""
        result = await data_service.process_document(str(sample_text_file))
        
        assert result["status"] == "success"
        assert "file_path" in result
        assert "chunks" in result
    
    @pytest.mark.asyncio
    async def test_process_document_pdf(self, data_service, sample_pdf_file):
        """Test processing a PDF document."""
        result = await data_service.process_document(str(sample_pdf_file))
        
        assert result["status"] == "success"
        assert "file_path" in result
    
    @pytest.mark.asyncio
    async def test_process_document_unsupported(self, data_service, temp_dir):
        """Test processing an unsupported document type."""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("Unsupported content")
        
        result = await data_service.process_document(str(unsupported_file))
        
        assert result["status"] == "error"
        assert "Unsupported file type" in result["error"]
    
    def test_get_documents(self, data_service, sample_text_file):
        """Test getting list of processed documents."""
        # Process a document first
        asyncio.run(data_service.process_document(str(sample_text_file)))
        
        documents = data_service.get_documents()
        
        assert isinstance(documents, list)
        assert len(documents) > 0
        assert any(doc["file_path"] == str(sample_text_file) for doc in documents)
    
    def test_delete_document(self, data_service, sample_text_file):
        """Test deleting a processed document."""
        # Process a document first
        asyncio.run(data_service.process_document(str(sample_text_file)))
        
        # Delete the document
        result = data_service.delete_document(str(sample_text_file))
        
        assert result is True
        
        # Verify it's deleted
        documents = data_service.get_documents()
        assert not any(doc["file_path"] == str(sample_text_file) for doc in documents)


class TestLoggingService:
    """Test cases for LoggingService."""
    
    @pytest.fixture
    def logging_service(self, temp_dir):
        """Create a logging service instance for testing."""
        log_file = temp_dir / "test.log"
        return LoggingService(log_file=str(log_file))
    
    def test_get_logger(self, logging_service):
        """Test getting a logger instance."""
        logger = logging_service.get_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
    
    def test_log_operation(self, logging_service):
        """Test logging an operation."""
        logger = logging_service.get_logger("test")
        
        # This should not raise an exception
        logging_service._log_operation("test_operation", True, {"key": "value"})
    
    def test_get_logs(self, logging_service):
        """Test getting log entries."""
        logs = logging_service.get_logs()
        
        assert isinstance(logs, list)
    
    def test_clear_logs(self, logging_service):
        """Test clearing log entries."""
        # This should not raise an exception
        logging_service.clear_logs()


class TestChatHistoryService:
    """Test cases for ChatHistoryService."""
    
    @pytest.fixture
    def chat_history_service(self, temp_dir):
        """Create a chat history service instance for testing."""
        db_path = temp_dir / "chat_history.db"
        return ChatHistoryService(db_path=str(db_path))
    
    def test_add_message(self, chat_history_service):
        """Test adding a message to chat history."""
        message = {
            "role": "user",
            "content": "Hello",
            "timestamp": "2023-01-01T00:00:00"
        }
        
        result = chat_history_service.add_message(message)
        
        assert result is True
    
    def test_get_history(self, chat_history_service):
        """Test getting chat history."""
        # Add some messages first
        messages = [
            {"role": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00"},
            {"role": "assistant", "content": "Hi", "timestamp": "2023-01-01T00:01:00"}
        ]
        
        for message in messages:
            chat_history_service.add_message(message)
        
        history = chat_history_service.get_history()
        
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Hi"
    
    def test_clear_history(self, chat_history_service):
        """Test clearing chat history."""
        # Add some messages first
        chat_history_service.add_message({
            "role": "user",
            "content": "Hello",
            "timestamp": "2023-01-01T00:00:00"
        })
        
        # Clear history
        chat_history_service.clear_history()
        
        # Verify it's cleared
        history = chat_history_service.get_history()
        assert len(history) == 0


class TestRepositoryService:
    """Test cases for RepositoryService."""
    
    @pytest.fixture
    def repository_service(self, temp_dir):
        """Create a repository service instance for testing."""
        return RepositoryService(github_dir=str(temp_dir / "github"))
    
    @pytest.mark.asyncio
    async def test_clone_repository_success(self, repository_service, temp_dir):
        """Test successful repository cloning."""
        repo_url = "https://github.com/test/repo.git"
        local_path = temp_dir / "github" / "test-repo"
        
        with patch('git.Repo.clone_from') as mock_clone:
            mock_repo = Mock()
            mock_clone.return_value = mock_repo
            
            result = await repository_service.clone_repository(repo_url, str(local_path))
            
            assert result is True
            mock_clone.assert_called_once_with(repo_url, str(local_path), branch="main")
    
    @pytest.mark.asyncio
    async def test_clone_repository_failure(self, repository_service, temp_dir):
        """Test repository cloning failure."""
        repo_url = "https://github.com/invalid/repo.git"
        local_path = temp_dir / "github" / "invalid-repo"
        
        with patch('git.Repo.clone_from', side_effect=Exception("Clone failed")):
            result = await repository_service.clone_repository(repo_url, str(local_path))
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_update_repository_success(self, repository_service, temp_dir):
        """Test successful repository update."""
        local_path = temp_dir / "github" / "test-repo"
        local_path.mkdir(parents=True)
        
        with patch('git.Repo') as mock_repo_class:
            mock_repo = Mock()
            mock_origin = Mock()
            mock_repo.remotes.origin = mock_origin
            mock_repo_class.return_value = mock_repo
            
            result = await repository_service.update_repository(str(local_path))
            
            assert result is True
            mock_origin.pull.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_repository_not_found(self, repository_service, temp_dir):
        """Test repository update when repository not found."""
        local_path = temp_dir / "github" / "nonexistent-repo"
        
        result = await repository_service.update_repository(str(local_path))
        
        assert result is False
    
    def test_get_repository_files(self, repository_service, temp_dir):
        """Test getting files from repository."""
        repo_path = temp_dir / "github" / "test-repo"
        repo_path.mkdir(parents=True)
        
        # Create some test files
        (repo_path / "test.py").write_text("print('test')")
        (repo_path / "README.md").write_text("# Test")
        
        files = repository_service.get_repository_files(str(repo_path), [".py", ".md"])
        
        assert len(files) == 2
        assert any("test.py" in f for f in files)
        assert any("README.md" in f for f in files)
    
    def test_get_repository_files_no_extensions(self, repository_service, temp_dir):
        """Test getting files without extension filtering."""
        repo_path = temp_dir / "github" / "test-repo"
        repo_path.mkdir(parents=True)
        
        # Create some test files
        (repo_path / "test.py").write_text("print('test')")
        (repo_path / "README.md").write_text("# Test")
        (repo_path / "binary.dat").write_bytes(b"binary content")
        
        files = repository_service.get_repository_files(str(repo_path))
        
        assert len(files) == 3  # All files should be included


class TestFileProcessor:
    """Test cases for FileProcessor."""
    
    @pytest.fixture
    def file_processor(self):
        """Create a file processor instance for testing."""
        return FileProcessor()
    
    def test_extract_text_from_pdf(self, file_processor, sample_pdf_file):
        """Test extracting text from PDF file."""
        text = file_processor.extract_text_from_pdf(str(sample_pdf_file))
        
        assert isinstance(text, str)
        assert len(text) > 0
    
    def test_extract_text_from_markdown(self, file_processor, sample_markdown_file):
        """Test extracting text from markdown file."""
        text = file_processor.extract_text_from_markdown(str(sample_markdown_file))
        
        assert isinstance(text, str)
        assert "# Test Document" in text
        assert "test_function" in text
    
    def test_extract_text_from_text(self, file_processor, sample_text_file):
        """Test extracting text from plain text file."""
        text = file_processor.extract_text_from_text(str(sample_text_file))
        
        assert isinstance(text, str)
        assert "test document" in text.lower()
    
    def test_extract_text_unsupported(self, file_processor, temp_dir):
        """Test extracting text from unsupported file type."""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("Unsupported content")
        
        text = file_processor.extract_text(str(unsupported_file))
        
        assert text == "Unsupported file type: .xyz"
    
    def test_chunk_text(self, file_processor):
        """Test chunking text into smaller pieces."""
        text = "This is a test document. " * 100  # Create longer text
        
        chunks = file_processor.chunk_text(text, chunk_size=50, chunk_overlap=10)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) <= 50 for chunk in chunks)
    
    def test_chunk_text_empty(self, file_processor):
        """Test chunking empty text."""
        chunks = file_processor.chunk_text("", chunk_size=50, chunk_overlap=10)
        
        assert chunks == []
    
    def test_chunk_text_single_chunk(self, file_processor):
        """Test chunking text that fits in a single chunk."""
        text = "Short text"
        
        chunks = file_processor.chunk_text(text, chunk_size=50, chunk_overlap=10)
        
        assert len(chunks) == 1
        assert chunks[0] == text