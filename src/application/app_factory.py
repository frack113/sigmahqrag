"""
Application Factory for SigmaHQ RAG application.

Provides a high-level factory for creating and configuring the complete application
with all services properly integrated and configured.
"""

import time
from dataclasses import dataclass
from typing import Any

from ..core import ChatService, LLMService, RAGService
from ..infrastructure import (
    FileProcessor,
    FileStorage,
    GitHubClient,
    LMStudioClient,
    SQLiteManager,
)
from ..shared import (
    DEFAULT_CONFIG,
    SERVICE_APPLICATION,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    BaseService,
)


@dataclass
class ApplicationStats:
    """Statistics for the application."""
    startup_time: float = 0.0
    services_initialized: int = 0
    services_healthy: int = 0
    total_errors: int = 0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class Application(BaseService):
    """
    Complete SigmaHQ RAG application with all integrated services.
    
    This class provides a high-level interface for the entire application,
    managing all services and their interactions.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the application.
        
        Args:
            config: Application configuration
        """
        BaseService.__init__(self, f"{SERVICE_APPLICATION}.application")
        
        # Configuration
        self.config = config or {}
        
        # Services
        self.llm_service: LLMService | None = None
        self.rag_service: RAGService | None = None
        self.chat_service: ChatService | None = None
        self.database_manager: SQLiteManager | None = None
        self.file_processor: FileProcessor | None = None
        self.file_storage: FileStorage | None = None
        self.github_client: GitHubClient | None = None
        self.lm_studio_client: LMStudioClient | None = None
        
        # Statistics
        self.stats = ApplicationStats()
        self._start_time = time.time()
        
        # Service registry
        self.services: list[BaseService] = []

    async def initialize(self) -> bool:
        """
        Initialize all application services.
        
        Returns:
            True if initialization successful, False otherwise
        """
        startup_start = time.time()
        
        try:
            # Initialize core services
            await self._initialize_core_services()
            
            # Initialize infrastructure services
            await self._initialize_infrastructure_services()
            
            # Initialize application services
            await self._initialize_application_services()
            
            # Verify all services are healthy
            healthy_services = sum(1 for service in self.services if self._is_service_healthy(service))
            self.stats.services_healthy = healthy_services
            self.stats.services_initialized = len(self.services)
            
            self.stats.startup_time = time.time() - startup_start
            
            if healthy_services == len(self.services):
                self.logger.info(f"Application initialized successfully with {len(self.services)} services")
                return True
            else:
                self.logger.warning(f"Application initialized with {len(self.services) - healthy_services} unhealthy services")
                return False
                
        except Exception as e:
            self.stats.total_errors += 1
            self.stats.last_error = str(e)
            self.logger.error(f"Application initialization failed: {e}")
            return False

    async def _initialize_core_services(self) -> None:
        """Initialize core business logic services."""
        # Initialize LLM service
        llm_config = self.config.get("llm", DEFAULT_CONFIG["llm"])
        self.llm_service = LLMService(config=llm_config)
        await self.llm_service.initialize()
        self.services.append(self.llm_service)
        
        # Initialize RAG service
        rag_config = self.config.get("rag", DEFAULT_CONFIG["rag"])
        rag_database_config = self.config.get("database", DEFAULT_CONFIG["database"])
        self.rag_service = RAGService(
            llm_service=self.llm_service,
            config=rag_config,
            database_config=rag_database_config
        )
        await self.rag_service.initialize()
        self.services.append(self.rag_service)
        
        # Initialize Chat service
        chat_config = self.config.get("chat", DEFAULT_CONFIG["chat"])
        self.chat_service = ChatService(
            llm_service=self.llm_service,
            rag_service=self.rag_service,
            **chat_config
        )
        await self.chat_service.initialize()
        self.services.append(self.chat_service)

    async def _initialize_infrastructure_services(self) -> None:
        """Initialize infrastructure services."""
        # Initialize database manager
        db_config = self.config.get("database", DEFAULT_CONFIG["database"])
        self.database_manager = SQLiteManager(**db_config)
        self.services.append(self.database_manager)
        
        # Initialize file processor
        file_processor_config = self.config.get("file_processor", DEFAULT_CONFIG["performance"])
        self.file_processor = FileProcessor(**file_processor_config)
        self.services.append(self.file_processor)
        
        # Initialize file storage
        file_storage_config = self.config.get("file_storage", DEFAULT_CONFIG["performance"])
        self.file_storage = FileStorage(**file_storage_config)
        self.services.append(self.file_storage)
        
        # Initialize GitHub client
        github_config = self.config.get("github_client", DEFAULT_CONFIG["performance"])
        self.github_client = GitHubClient(**github_config)
        self.services.append(self.github_client)
        
        # Initialize LM Studio client
        lm_studio_config = self.config.get("lm_studio_client", DEFAULT_CONFIG["performance"])
        self.lm_studio_client = LMStudioClient(**lm_studio_config)
        self.services.append(self.lm_studio_client)

    async def _initialize_application_services(self) -> None:
        """Initialize application-level services."""
        # Application services are initialized as part of core and infrastructure
        pass

    def _is_service_healthy(self, service: BaseService) -> bool:
        """Check if a service is healthy."""
        try:
            health_status = service.get_health_status()
            return health_status["status"] == STATUS_HEALTHY
        except Exception:
            return False

    def get_service_health(self) -> dict[str, Any]:
        """Get health status of all services."""
        service_health = {}
        
        for service in self.services:
            try:
                health_status = service.get_health_status()
                service_health[service.service_name] = health_status
            except Exception as e:
                service_health[service.service_name] = {
                    "status": STATUS_UNHEALTHY,
                    "error": str(e),
                    "timestamp": time.time(),
                }
        
        return service_health

    def get_overall_health(self) -> dict[str, Any]:
        """Get overall application health status."""
        service_health = self.get_service_health()
        
        healthy_services = sum(1 for health in service_health.values() if health.get("status") == STATUS_HEALTHY)
        total_services = len(service_health)
        
        status = STATUS_HEALTHY
        issues = []
        
        if healthy_services < total_services:
            status = STATUS_DEGRADED
            unhealthy_services = [name for name, health in service_health.items() if health.get("status") != STATUS_HEALTHY]
            issues.append(f"Unhealthy services: {', '.join(unhealthy_services)}")
        
        # Check for critical service failures
        critical_services = ["llm_service", "rag_service", "chat_service"]
        critical_failures = [name for name in critical_services if name in service_health and service_health[name].get("status") == STATUS_UNHEALTHY]
        
        if critical_failures:
            status = STATUS_UNHEALTHY
            issues.append(f"Critical service failures: {', '.join(critical_failures)}")
        
        return {
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "services": {
                "total": total_services,
                "healthy": healthy_services,
                "unhealthy": total_services - healthy_services,
            },
            "service_details": service_health,
            "stats": {
                "startup_time": self.stats.startup_time,
                "services_initialized": self.stats.services_initialized,
                "services_healthy": self.stats.services_healthy,
                "total_errors": self.stats.total_errors,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics for all services."""
        stats = {
            "application": {
                "startup_time": self.stats.startup_time,
                "services_initialized": self.stats.services_initialized,
                "services_healthy": self.stats.services_healthy,
                "total_errors": self.stats.total_errors,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "services": {},
        }
        
        for service in self.services:
            try:
                service_stats = service.get_usage_stats()
                stats["services"][service.service_name] = service_stats
            except Exception as e:
                stats["services"][service.service_name] = {"error": str(e)}
        
        return stats

    def cleanup(self) -> None:
        """Clean up all services."""
        try:
            # Clean up services in reverse order
            for service in reversed(self.services):
                try:
                    service.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up service {service.service_name}: {e}")
            
            self.logger.info("Application cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during application cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


def create_application(config: dict[str, Any] | None = None) -> Application:
    """
    Create a fully configured SigmaHQ RAG application.
    
    Args:
        config: Application configuration
        
    Returns:
        Configured application instance
    """
    return Application(config=config)


# Convenience function for quick application creation
def create_default_application() -> Application:
    """Create an application with default configuration."""
    return create_application()


# Example configuration
DEFAULT_APPLICATION_CONFIG = {
    "llm_service": {
        "model": "default",
        "base_url": "http://localhost:1234",
        "api_key": "lm-studio",
        "timeout": 30,
        "max_retries": 3,
    },
    "rag_service": {
        "model": "default",
        "base_url": "http://localhost:1234",
        "api_key": "lm-studio",
        "chunk_size": 1000,
        "chunk_overlap": 200,
    },
    "rag_database": {
        "path": "./data/rag_db",
        "max_connections": 5,
        "timeout": 30,
    },
    "chat_service": {
        "conversation_history_limit": 50,
    },
    "database": {
        "db_path": "./data/app.db",
        "max_connections": 5,
        "timeout": 30,
    },
    "file_processor": {
        "allowed_extensions": [".txt", ".md", ".pdf", ".docx", ".doc", ".csv", ".json", ".xml"],
        "max_file_size_mb": 50,
        "temp_dir": "./temp",
        "chunk_size": 1000,
        "chunk_overlap": 200,
    },
    "file_storage": {
        "upload_dir": "./uploads",
        "allowed_extensions": [".txt", ".md", ".pdf", ".docx", ".doc", ".csv", ".json", ".xml"],
        "max_file_size_mb": 50,
        "max_storage_size_gb": 10,
    },
    "github_client": {
        "api_base_url": "https://api.github.com",
        "token": None,
        "rate_limit_delay": 1.0,
    },
    "lm_studio_client": {
        "base_url": "http://localhost:1234",
        "timeout": 30,
        "max_retries": 3,
    },
}