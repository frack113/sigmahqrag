"""
Local Embedding Service for SigmaHQ RAG application.

Provides CPU-based embeddings using sentence-transformers for reliable operation
without external dependencies. Includes fallback mechanisms for LM Studio API.
"""

import time
from typing import Any

from ..shared import (
    SERVICE_EMBEDDING,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    AsyncComponent,
    BaseService,
    EmbeddingConfig,
    EmbeddingError,
    NetworkError,
    get_cpu_usage,
    get_memory_usage,
    handle_service_errors,
    rate_limit,
    retry_with_backoff,
)


class LocalEmbeddingService(BaseService, AsyncComponent):
    """
    Local embedding service using sentence-transformers.
    
    Features:
    - CPU-based embeddings with sentence-transformers/all-MiniLM-L6-v2
    - Fallback to LM Studio API if local embeddings fail
    - Performance optimization with caching
    - Comprehensive error handling and monitoring
    """

    def __init__(self, config: EmbeddingConfig | None = None):
        """
        Initialize the local embedding service.
        
        Args:
            config: Embedding configuration
        """
        BaseService.__init__(self, f"{SERVICE_EMBEDDING}.local_embedding_service")
        AsyncComponent.__init__(self)
        
        # Configuration
        self.config = config or self._get_default_config()
        
        # Service state
        self.model = None
        self._initialized = False
        self._start_time = time.time()
        
        # Statistics
        self.total_embeddings = 0
        self.cpu_embeddings = 0
        self.api_fallbacks = 0
        self.failed_embeddings = 0
        self.average_response_time = 0.0
        self.last_error = None
        
        # Initialize service
        self._initialize_model()

    def _get_default_config(self) -> EmbeddingConfig:
        """Get default embedding configuration."""
        return EmbeddingConfig(
            model="all-MiniLM-L6-v2",
            base_url="http://localhost:1234",
            api_key="lm-studio",
            chunk_size=1000,
            chunk_overlap=200,
        )

    async def initialize(self) -> bool:
        """
        Initialize the embedding service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
            
        try:
            success = self._initialize_model()
            if success:
                self._initialized = True
                self._log_operation("Local embedding service initialization", True)
                self.logger.info(f"Local embedding service initialized with model: {self.config['model']}")
            else:
                self._log_operation("Local embedding service initialization", False)
                self.logger.error("Local embedding service initialization failed")
            
            return success
        except Exception as e:
            self._log_operation("Local embedding service initialization", False, {"error": str(e)})
            self.logger.error(f"Local embedding service initialization failed: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.model:
                del self.model
                self.model = None

            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

            self._initialized = False
            self._log_operation("Local embedding service cleanup", True)
            
        except Exception as e:
            self._log_operation("Local embedding service cleanup", False, {"error": str(e)})
            self.logger.error(f"Error during local embedding service cleanup: {e}")

    def _initialize_model(self) -> bool:
        """Initialize the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            self.logger.info(f"Loading sentence-transformers model: {self.config['model']}")
            self.model = SentenceTransformer(self.config['model'])
            
            # Test the model with a simple embedding
            test_embedding = self.model.encode(["test"])
            if len(test_embedding) > 0:
                self.logger.info("Sentence-transformers model loaded successfully")
                return True
            else:
                self.logger.error("Failed to generate test embedding")
                return False
                
        except ImportError as e:
            self.logger.warning(f"sentence-transformers not available: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error initializing sentence-transformers model: {e}")
            return False

    @handle_service_errors(error_types=[EmbeddingError, NetworkError], default_message="Local embedding generation failed")
    @retry_with_backoff(max_retries=2, base_delay=1.0, max_delay=5.0)
    @rate_limit(max_calls=50, time_window=60)  # 50 calls per minute
    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using local sentence-transformers model.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        start_time = time.time()
        
        try:
            if self.model is None:
                if not self._initialize_model():
                    raise EmbeddingError("Failed to initialize local embedding model")
            
            # Generate embeddings
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            # Convert to list format
            embeddings_list = embeddings.tolist()
            
            # Update statistics
            self.total_embeddings += len(texts)
            self.cpu_embeddings += len(texts)
            
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            self.logger.info(f"Generated {len(texts)} embeddings locally in {response_time:.2f}s")
            return embeddings_list
            
        except Exception as e:
            self.failed_embeddings += len(texts)
            self.last_error = str(e)
            self.logger.error(f"Local embedding generation failed: {e}")
            raise EmbeddingError(f"Local embedding failed: {str(e)}")

    async def generate_embeddings_with_fallback(
        self, texts: list[str], use_fallback: bool = True
    ) -> list[list[float]]:
        """
        Generate embeddings with fallback to LM Studio API.
        
        Args:
            texts: List of text strings to embed
            use_fallback: Whether to use LM Studio API as fallback
            
        Returns:
            List of embedding vectors
        """
        try:
            # Try local embeddings first
            return await self.generate_embeddings(texts)
            
        except EmbeddingError as e:
            if use_fallback:
                self.logger.warning(f"Local embeddings failed, falling back to LM Studio API: {e}")
                return await self._generate_embeddings_via_api(texts)
            else:
                raise

    async def _generate_embeddings_via_api(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings via LM Studio API as fallback.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            import requests

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['api_key']}",
            }

            # LM Studio expects the input as a string or array of strings
            payload = {"model": self.config['model'], "input": texts}

            response = requests.post(
                f"{self.config['base_url']}/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            # Extract embeddings from the response
            embeddings = []
            for item in data.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
                else:
                    self.logger.warning("No embedding found in API response item")
                    embeddings.append([])

            # Update statistics
            self.total_embeddings += len(texts)
            self.api_fallbacks += len(texts)
            
            self.logger.info(f"Generated {len(texts)} embeddings via API")
            return embeddings

        except Exception as e:
            self.failed_embeddings += len(texts)
            self.last_error = str(e)
            self.logger.error(f"API embedding generation failed: {e}")
            raise EmbeddingError(f"API embedding failed: {str(e)}")

    def get_embedding_stats(self) -> dict[str, Any]:
        """Get embedding service statistics."""
        return {
            "total_embeddings": self.total_embeddings,
            "cpu_embeddings": self.cpu_embeddings,
            "api_fallbacks": self.api_fallbacks,
            "failed_embeddings": self.failed_embeddings,
            "success_rate": self._calculate_success_rate(),
            "average_response_time": self.average_response_time,
            "memory_usage_mb": get_memory_usage().get("rss_mb", 0),
            "cpu_usage_percent": get_cpu_usage(),
            "last_error": self.last_error,
            "uptime_seconds": time.time() - self._start_time,
        }

    def _calculate_success_rate(self) -> float:
        """Calculate embedding success rate."""
        total = self.total_embeddings + self.failed_embeddings
        if total == 0:
            return 0.0
        return (self.total_embeddings / total) * 100

    def _update_response_time(self, response_time: float):
        """Update average response time using moving average."""
        if self.total_embeddings == 0:
            self.average_response_time = response_time
        else:
            # Moving average: new_avg = (old_avg * (n-1) + new_value) / n
            n = self.total_embeddings
            self.average_response_time = (
                (self.average_response_time * (n - 1)) + response_time
            ) / n

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []
        
        # Check if model is loaded
        if self.model is None:
            status = STATUS_UNHEALTHY
            issues.append("Embedding model not loaded")
        
        # Check success rate
        success_rate = self._calculate_success_rate()
        if success_rate < 80:  # Less than 80% success rate
            status = STATUS_DEGRADED
            issues.append(f"Low success rate: {success_rate:.1f}%")
        
        # Check response time
        if self.average_response_time > 10.0:  # More than 10 seconds average
            status = STATUS_DEGRADED
            issues.append(f"High response time: {self.average_response_time:.2f}s")
        
        # Check memory usage
        memory_info = get_memory_usage()
        if memory_info.get("rss_mb", 0) > 1024.0:  # More than 1GB
            status = STATUS_DEGRADED
            issues.append(f"High memory usage: {memory_info.get('rss_mb', 0):.2f}MB")
        
        return {
            "service": SERVICE_EMBEDDING,
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": self.get_embedding_stats(),
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config": self.config,
            "stats": self.get_embedding_stats(),
            "health": self.get_health_status(),
        }

    def update_config(self, new_config: EmbeddingConfig) -> bool:
        """Update embedding configuration."""
        try:
            self.config = new_config
            self.logger.info(f"Embedding configuration updated: {new_config['model']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update embedding configuration: {e}")
            return False


# Convenience factory functions
def create_local_embedding_service(config: EmbeddingConfig | None = None) -> LocalEmbeddingService:
    """Create a local embedding service with default configuration."""
    return LocalEmbeddingService(config=config)


def create_cpu_embedding_service() -> LocalEmbeddingService:
    """Create a CPU-based embedding service."""
    config = EmbeddingConfig(
        model="all-MiniLM-L6-v2",
        base_url="http://localhost:1234",
        api_key="lm-studio",
        chunk_size=1000,
        chunk_overlap=200,
    )
    return LocalEmbeddingService(config=config)


# Backward compatibility alias
OptimizedLocalEmbeddingService = LocalEmbeddingService