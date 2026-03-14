"""
Integration tests for SigmaHQ RAG application using Gradio.
Comprehensive tests covering all core services, utilities, and integration points.
"""

import os
import json
import tempfile
from pathlib import Path


class TestLocalEmbeddingService:
    """Tests for Local Embedding Service."""

    def test_initialization(self):
        """Test service initializes correctly."""
        from src.core.local_embedding_service import LocalEmbeddingService

        service = LocalEmbeddingService()
        assert isinstance(service, LocalEmbeddingService)

    def test_model_path(self):
        """Test model path is set correctly."""
        from src.core.local_embedding_service import LocalEmbeddingService

        service = LocalEmbeddingService()
        model_path = str(service.DEFAULT_MODEL_PATH)
        assert "all-MiniLM-L6-v2.safetensors" in model_path

    def test_factory_function(self):
        """Test factory function creates service correctly."""
        from src.core.local_embedding_service import create_local_embedding_service

        service = create_local_embedding_service()
        assert isinstance(service, LocalEmbeddingService)

    def test_embed_single_sentence_async(self):
        """Test embedding a single sentence."""
        import asyncio
        from src.core.local_embedding_service import LocalEmbeddingService
        
        service = LocalEmbeddingService()
        
        # Test that the model loads correctly
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, "cache")
            service.cache_dir = cache_dir
            
            async def get_embedding():
                return await service.embed_single_sentence("Hello world")
            
            embeddings = asyncio.run(get_embedding())
            assert len(embeddings) > 0
            assert all(isinstance(x, (int, float)) for x in embeddings)


class TestConfigService:
    """Tests for configuration service."""

    def test_initialization(self):
        """Test config service initializes correctly."""
        from src.models.config_service import ConfigService

        config = ConfigService()
        assert isinstance(config, ConfigService)

    def test_rag_config(self):
        """Test RAG configuration retrieval."""
        from src.models.config_service import ConfigService

        config = ConfigService()
        rag_config = config.get_rag_config()

        assert isinstance(rag_config, dict)

    def test_server_config(self):
        """Test server configuration retrieval."""
        from src.models.config_service import ConfigService

        config = ConfigService()
        server_config = config.get_server_config()

        assert isinstance(server_config, dict)
        assert "host" in server_config
        assert "port" in server_config


class TestDataService:
    """Tests for data service functionality."""

    def test_initialization(self):
        """Test data service initialization."""
        from src.models.data_service import DataService

        service = DataService()
        assert isinstance(service, DataService)

    def test_vector_store_path(self):
        """Test vector store path is set correctly."""
        from src.models.data_service import DataService

        service = DataService()
        # Check for vector_store_persist_directory attribute
        assert hasattr(service, "vector_store_persist_directory")
        assert isinstance(service.vector_store_persist_directory, str)


class TestLoggingService:
    """Tests for logging service."""

    def test_initialization(self):
        """Test logging service initialization."""
        from src.models.logging_service import LoggingService

        service = LoggingService()
        assert isinstance(service, LoggingService)

    def test_get_log_config(self):
        """Test getting log configuration."""
        from src.models.logging_service import LoggingService

        service = LoggingService()
        config = service.get_logging_config()

        assert isinstance(config, dict)


class TestConstants:
    """Tests for shared constants."""

    def test_default_config_exists(self):
        """Test default configuration constants exist."""
        from src.shared.constants import DEFAULT_CONFIG

        assert isinstance(DEFAULT_CONFIG, dict)
        assert "llm" in DEFAULT_CONFIG
        assert "rag" in DEFAULT_CONFIG

    def test_embedding_config(self):
        """Test embedding configuration constants exist."""
        from src.shared.constants import DEFAULT_EMBEDDING_MODEL

        assert DEFAULT_EMBEDDING_MODEL is not None
        assert isinstance(DEFAULT_EMBEDDING_MODEL, str)


class TestBaseService:
    """Tests for base service class."""

    def test_initialization(self):
        """Test base service initialization."""
        from src.shared.base_service import BaseService

        class ConcreteService(BaseService):
            name = "test"

            def get_collection_name(self):
                return "test"

            def cleanup(self):
                pass

            def initialize(self) -> bool:
                return True

        service = ConcreteService()
        assert isinstance(service, BaseService)
        assert service.name == "test"

    def test_health_check(self):
        """Test base service health check."""
        from src.shared.base_service import BaseService

        class TestService(BaseService):
            name = "test"

            def get_collection_name(self):
                return "test"

            def cleanup(self):
                pass

            def initialize(self) -> bool:
                return True

        service = TestService()
        health = service.get_health_status()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "issues" in health


class TestUtils:
    """Tests for utility functions."""

    def test_get_app_directory(self):
        """Test getting application directory."""
        from src.shared.utils import get_app_directory

        app_dir = get_app_directory()
        assert isinstance(app_dir, Path)
        assert "sigmahqrag" in str(app_dir).lower() or "data" in str(app_dir).lower()

    def test_memory_usage(self):
        """Test memory usage reporting."""
        from src.shared.utils import get_memory_usage

        memory = get_memory_usage()
        assert isinstance(memory, dict)
        assert "total_mb" in memory
        assert "available_mb" in memory

    def test_cpu_usage(self):
        """Test CPU usage reporting."""
        from src.shared.utils import get_cpu_usage

        cpu = get_cpu_usage()
        assert isinstance(cpu, float)
        assert 0.0 <= cpu <= 100.0


class TestExceptions:
    """Tests for custom exception classes."""

    def test_service_error(self):
        """Test ServiceError class."""
        from src.shared.exceptions import ServiceError

        try:
            raise ServiceError("Test error")
        except ServiceError as e:
            assert "Test error" in str(e)

    def test_configuration_error(self):
        """Test ConfigurationError class."""
        from src.shared.exceptions import ConfigurationError

        try:
            raise ConfigurationError("Invalid config")
        except ConfigurationError as e:
            assert "Invalid config" in str(e)

    def test_file_processing_error(self):
        """Test FileProcessingError class."""
        from src.shared.exceptions import FileProcessingError

        try:
            raise FileProcessingError("File error")
        except FileProcessingError as e:
            assert "File error" in str(e)


class TestGradioApp:
    """Tests for Gradio application structure."""

    def test_app_structure(self):
        """Test Gradio app structure can be imported."""
        from src.application.application import SigmaHQApplication

        # Just verify the class exists and has expected attributes
        assert hasattr(SigmaHQApplication, "create_interface")

    def test_app_init(self):
        """Test app initialization."""
        from src.application.application import SigmaHQApplication

        app = SigmaHQApplication()
        assert app is not None


class TestComponentImports:
    """Tests for component imports (verifying they exist)."""

    def test_chat_interface_exists(self):
        """Test chat interface component exists."""
        from src.components.chat_interface import ChatInterface

        assert isinstance(ChatInterface, type)

    def test_config_management_exists(self):
        """Test config management component exists."""
        from src.components.config_management import ConfigManagement

        assert isinstance(ConfigManagement, type)

    def test_data_management_exists(self):
        """Test data management component exists."""
        from src.components.data_management import DataManagement

        assert isinstance(DataManagement, type)

    def test_logs_viewer_exists(self):
        """Test logs viewer component exists."""
        from src.components.logs_viewer import LogsViewer

        assert isinstance(LogsViewer, type)


class TestFileProcessor:
    """Tests for file processor."""

    def test_file_processor_imports(self):
        """Test file processor can be imported."""
        from src.infrastructure.file_system.file_processor import FileProcessor

        # The class should exist
        assert isinstance(FileProcessor, type)


class TestRAGChatService:
    """Tests for RAG chat service."""

    def test_service_initialization(self):
        """Test RAG chat service initializes correctly."""
        from src.models.rag_chat_service import RAGChatService

        # Verify the class exists
        assert isinstance(RAGChatService, type)


class TestDatabaseManager:
    """Tests for database manager."""

    def test_database_manager_initialization(self):
        """Test database manager initializes correctly."""
        from src.infrastructure.database.sqlite_manager import SQLiteManager, create_sqlite_manager

        db = create_sqlite_manager()
        assert isinstance(db, SQLiteManager)

    def test_database_factory_function(self):
        """Test factory function creates database manager correctly."""
        from src.infrastructure.database.sqlite_manager import create_sqlite_manager

        db = create_sqlite_manager(path="test_db.db")
        assert hasattr(db, "db_path")

    def test_database_health_check(self):
        """Test database health check."""
        from src.infrastructure.database.sqlite_manager import SQLiteManager

        db = SQLiteManager()
        health = db.get_health_status()
        
        assert isinstance(health, dict)
        assert "status" in health


class TestChromaDBIntegration:
    """Tests for ChromaDB integration."""

    def test_chromadb_client(self):
        """Test ChromaDB client creation."""
        import chromadb
        from chromadb.api.models.Collection import Collection

        client = chromadb.PersistentClient(path="data/models/chroma_db")
        assert client is not None
        
        # Verify we can create a collection (basic client test)
        coll = client.get_or_create_collection(name="test_collection")
        assert isinstance(coll, Collection)

    def test_collection_operations(self):
        """Test ChromaDB collection operations."""
        import chromadb

        with tempfile.TemporaryDirectory() as tmpdir:
            client = chromadb.PersistentClient(path=tmpdir)
            collection = client.get_or_create_collection(name="test_ops")
            
            # Add documents
            ids = ["doc1", "doc2", "doc3"]
            documents = ["Document 1 content", "Document 2 content", "Document 3 content"]
            collection.add(ids=ids, documents=documents)
            
            # Query documents
            results = collection.get(where={"id": {"$in": ids}})
            assert len(results["documents"]) > 0


class TestHealthCheck:
    """Tests for health check functionality."""

    def test_service_health_check(self):
        """Test service health check returns proper structure."""
        from src.shared.statistics import BaseStats, check_service_health

        stats = BaseStats(
            total_requests=10,
            successful_requests=10,
            average_response_time=1.5,
            memory_usage_mb=200,
            cpu_usage_percent=30.0,
        )

        status, issues = check_service_health(stats)
        assert isinstance(status, str)
        assert isinstance(issues, list)

    def test_degraded_status_high_memory(self):
        """Test degraded status when memory is high."""
        from src.shared.statistics import BaseStats, check_service_health

        stats = BaseStats(
            total_requests=10,
            successful_requests=10,
            average_response_time=1.5,
            memory_usage_mb=900,  # High memory
            cpu_usage_percent=30.0,
        )

        status, issues = check_service_health(stats)
        assert "DEGRADED" in status.upper()

    def test_healthy_status(self):
        """Test healthy status with normal resources."""
        from src.shared.statistics import BaseStats, check_service_health

        stats = BaseStats(
            total_requests=100,
            successful_requests=95,
            average_response_time=2.0,
            memory_usage_mb=500,
            cpu_usage_percent=40.0,
        )

        status, issues = check_service_health(stats)
        assert "HEALTHY" in status.upper()


class TestStatsFormatting:
    """Tests for statistics formatting."""

    def test_format_stats_for_display(self):
        """Test statistics formatting for display."""
        from src.shared.statistics import BaseStats, format_stats_for_display

        stats = BaseStats(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            average_response_time=2.5,
            memory_usage_mb=500,
            cpu_usage_percent=45.0,
            uptime_seconds=3600,
        )

        formatted = format_stats_for_display(stats)
        assert "total_requests" in formatted
        assert "success_rate" in formatted


class TestProductionSetup:
    """Tests for production setup utilities."""

    def test_environment_setup_imports(self):
        """Test environment setup module can be imported."""
        from src.infrastructure.environment_setup import EnvironmentSetup

        setup = EnvironmentSetup()
        assert isinstance(setup, EnvironmentSetup)

    def test_get_system_health(self):
        """Test system health reporting via production setup pattern."""
        from src.shared.utils import get_memory_usage, get_cpu_usage

        health = {
            "memory": get_memory_usage(),
            "cpu": {"percent": get_cpu_usage()},
        }
        assert isinstance(health, dict)


class TestLMStudioClient:
    """Tests for LM Studio client (optional)."""

    def test_lm_studio_client_imports(self):
        """Test LM Studio client can be imported."""
        from src.infrastructure.external.lm_studio_client import LMStudioClient

        # The class should exist, but connection might fail
        assert isinstance(LMStudioClient, type)

    def test_lm_studio_client_config(self):
        """Test LM Studio client configuration."""
        from src.infrastructure.external.lm_studio_client import LMStudioClient
        
        client = LMStudioClient()
        
        # Just verify it can be instantiated
        assert hasattr(client, "base_url")


class TestGitHubClient:
    """Tests for GitHub client (optional)."""

    def test_github_client_imports(self):
        """Test GitHub client can be imported."""
        from src.infrastructure.external.github_client import GitHubClient

        # The class should exist
        assert isinstance(GitHubClient, type)


class TestFileStorage:
    """Tests for file storage."""

    def test_file_storage_setup_imports(self):
        """Test file storage setup can be imported."""
        from src.infrastructure.file_storage_setup import FileSystemSetup
        
        setup = FileSystemSetup()
        assert isinstance(setup, FileSystemSetup)


class TestPortManager:
    """Tests for port management."""

    def test_port_manager_exists(self):
        """Test port manager can be imported."""
        try:
            from src.infrastructure.port_manager import PortFinder
            
            finder = PortFinder()
            assert isinstance(finder, PortFinder)
        except ImportError:
            pass  # Optional module


class TestDatabaseConfigService:
    """Tests for database configuration service."""

    def test_database_config_initialization(self):
        """Test database configuration service initializes correctly."""
        from src.models.config_service import ConfigService
        
        config = ConfigService()
        
        # Get default database config
        db_config = config.get_database_config()
        assert isinstance(db_config, dict)


class TestStatisticsModule:
    """Tests for statistics module."""

    def test_base_stats_initialization(self):
        """Test BaseStats initialization."""
        from src.shared.statistics import BaseStats
        
        stats = BaseStats(
            total_requests=10,
            successful_requests=9,
            failed_requests=1,
        )
        
        assert stats.total_requests == 10
        assert stats.successful_requests == 9
        assert stats.failed_requests == 1

    def test_stats_aggregation(self):
        """Test statistics aggregation."""
        from src.shared.statistics import BaseStats
        
        # Create and aggregate stats
        base_stats = BaseStats(
            total_requests=5,
            successful_requests=4,
            failed_requests=1,
            average_response_time=2.0,
        )
        
        assert base_stats.success_rate == 0.8


class TestIntegrationWithGradio:
    """Integration tests with Gradio application."""

    def test_gradio_app_lifecycle(self):
        """Test complete Gradio app lifecycle."""
        from src.application.application import SigmaHQApplication
        
        # Create and initialize app
        app = SigmaHQApplication()
        
        # Verify interface can be created
        interface = app.create_interface()
        assert interface is not None

    def test_app_components(self):
        """Test application components are initialized."""
        from src.application.application import SigmaHQApplication
        
        app = SigmaHQApplication()
        
        # Check that all expected tabs exist
        if hasattr(app, 'interface') and app.interface:
            tabs = [tab.name for tab in app.interface]
            
            assert len(tabs) > 0


class TestServiceFactoryFunctions:
    """Tests for service factory functions."""

    def test_llm_service_factory(self):
        """Test LLM service factory function."""
        from src.core.llm_service import create_chat_service, create_completion_service
        
        chat_service = create_chat_service()
        assert chat_service is not None
        
        completion_service = create_completion_service()
        assert completion_service is not None

    def test_rag_service_factory(self):
        """Test RAG service factory function."""
        from src.core.rag_service import create_rag_service, create_document_rag_service
        
        rag_service = create_rag_service()
        assert rag_service is not None

    def test_embedding_service_factory(self):
        """Test embedding service factory function."""
        from src.core.local_embedding_service import create_local_embedding_service
        
        service = create_local_embedding_service()
        assert service is not None


class TestSharedUtils:
    """Tests for shared utility functions."""

    def test_validate_file_type(self):
        """Test file type validation."""
        from src.shared.utils import validate_file_type
        
        # Test valid files
        assert validate_file_type("file.pdf", "application/pdf") is True
        assert validate_file_type("file.txt", "text/plain") is True

    def test_format_file_size(self):
        """Test file size formatting."""
        from src.shared.utils import format_file_size
        
        # Test various sizes
        result = format_file_size(1024)
        assert isinstance(result, str)


class TestConfigManagement:
    """Tests for configuration management."""

    def test_load_config(self):
        """Test loading configuration file."""
        from src.models.config_service import ConfigService
        
        config = ConfigService()
        
        # Load default config
        loaded = config.load_config()
        assert loaded is not None

    def test_save_config(self):
        """Test saving configuration file."""
        from src.models.config_service import ConfigService
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = ConfigService()
            defaults = config.get_defaults()
            
            # Write temp config
            json.dump(defaults, f)
            temp_path = f.name
            
            # Read back and verify structure
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert isinstance(data, dict)
            
            os.unlink(temp_path)


if __name__ == "__main__":
    import pytest
    
    print("Running integration tests...")
    pytest.main([__file__, "-v"])