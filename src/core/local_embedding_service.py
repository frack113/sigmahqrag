"""
Local Embedding Service for SigmaHQ RAG application.

Provides standalone CPU-based embeddings using sentence-transformers with direct
safetensors model file loading. No external API dependencies required.
"""

import asyncio
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.shared import (
    SERVICE_EMBEDDING,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    AsyncComponent,
    BaseService,
    EmbeddingConfig,
    EmbeddingError,
    handle_service_errors,
)


class LocalEmbeddingService(BaseService, AsyncComponent):
    """
    Local embedding service using sentence-transformers.

    Features:
    - CPU-based embeddings with direct safetensors loading
    - No external API dependencies (LM Studio not required)
    - Optimized for async/Gradio integration using thread pool
    - Comprehensive error handling and monitoring
    """

    # Default model path - use the local safetensors file
    DEFAULT_MODEL_PATH = (
        Path(__file__).parent.parent.parent
        / "data"
        / "models"
        / "all-MiniLM-L6-v2.safetensors"
    )

    def __init__(self, config: EmbeddingConfig | dict[str, Any] | None = None):
        """
        Initialize the local embedding service.

        Args:
            config: Embedding configuration (EmbeddingConfig dataclass or dict)
        """
        BaseService.__init__(self, f"{SERVICE_EMBEDDING}.local_embedding_service")
        AsyncComponent.__init__(self)

        # Configuration - convert to dict if needed
        if isinstance(config, EmbeddingConfig):
            self.config = asdict(config)
        elif isinstance(config, dict):
            self.config = config
        else:
            self.config = self._get_default_config()

        # Service state
        self.model = None
        self._model_loaded = False
        self._start_time = time.time()

        # Statistics
        self.total_embeddings = 0
        self.failed_embeddings = 0
        self.average_response_time = 0.0
        self.last_error = None

        # Create thread pool executor for async-safe blocking calls
        self._executor: asyncio.ThreadPoolExecutor | None = None

    def _get_default_config(self) -> dict[str, Any]:
        """Get default embedding configuration with local model path."""
        return {
            "model_path": str(
                self.DEFAULT_MODEL_PATH
            ),  # Direct path to safetensors file
            "chunk_size": 1000,
            "chunk_overlap": 200,
        }

    async def initialize(self) -> bool:
        """Initialize the local embedding service."""
        if self._model_loaded:
            return True

        try:
            success = await asyncio.get_event_loop().run_in_executor(
                None, self._initialize_model_sync
            )
            if success:
                self._model_loaded = True
                self.logger.info(
                    f"Local embedding service initialized with model: {self.config.get('model_path', 'unknown')}"
                )
            else:
                self.logger.error("Local embedding service initialization failed")

            return success
        except Exception as e:
            self.logger.error(f"Local embedding service initialization failed: {e}")
            return False

    def _initialize_model_sync(self) -> bool:
        """Initialize the sentence-transformers model (sync)."""
        try:
            from sentence_transformers import SentenceTransformer

            model_path = self.config.get("model_path") or str(self.DEFAULT_MODEL_PATH)

            # Check if safetensors file exists
            if not Path(model_path).exists():
                self.logger.error(f"Model file not found: {model_path}")
                return False

            self.logger.info(f"Loading model from safetensors: {model_path}")
            self.model = SentenceTransformer(
                model_path,
                device="cpu",  # Force CPU for local embeddings
                trust_remote_code=False,
            )

            # Test the model with a simple embedding
            test_embedding = self.model.encode(["test"])
            if len(test_embedding) == 384:  # MiniLM produces 384-dim embeddings
                self.logger.info(
                    f"Model loaded successfully. Embedding dimension: {len(test_embedding)}"
                )
                return True
            else:
                self.logger.error(
                    f"Unexpected embedding dimension: {len(test_embedding)}"
                )
                return False

        except ImportError as e:
            self.logger.error(f"sentence-transformers not available: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.model is not None:
                del self.model
                self.model = None

            self._model_loaded = False
            self._log_operation("Local embedding service cleanup", True)

        except Exception as e:
            self._log_operation(
                "Local embedding service cleanup", False, {"error": str(e)}
            )
            self.logger.error(f"Error during local embedding service cleanup: {e}")

    @handle_service_errors(
        error_types=[EmbeddingError],
        default_message="Local embedding generation failed",
    )
    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using local sentence-transformers model.

        Uses thread pool executor to avoid blocking the async event loop.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        start_time = time.time()

        try:
            # Ensure model is loaded
            if self.model is None or not self._model_loaded:
                if not await self.initialize():
                    raise EmbeddingError("Failed to initialize local embedding model")

            # Generate embeddings in executor to avoid blocking async event loop
            # This is critical for Gradio compatibility - sentence-transformers is sync
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, self._embed_sync, texts
            )

            # Update statistics
            self.total_embeddings += len(texts)

            response_time = time.time() - start_time
            self._update_response_time(response_time, len(texts))

            self.logger.debug(
                f"Generated {len(texts)} embeddings in {response_time:.2f}s"
            )
            return embeddings

        except Exception as e:
            count = len(texts) if texts else 1
            self.failed_embeddings += count
            self.last_error = str(e)
            self.logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(f"Local embedding failed: {str(e)}")

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous embedding generation using the loaded model."""
        if self.model is None:
            raise EmbeddingError("Model not loaded. Call initialize() first.")

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def get_embedding_stats(self) -> dict[str, Any]:
        """Get embedding service statistics."""
        return {
            "total_embeddings": self.total_embeddings,
            "failed_embeddings": self.failed_embeddings,
            "success_rate": self._calculate_success_rate(),
            "average_response_time": self.average_response_time,
            "memory_usage_mb": 0,  # Would need psutil for accurate memory
            "cpu_usage_percent": 0,  # Would need psutil for accurate CPU
            "last_error": self.last_error,
            "uptime_seconds": time.time() - self._start_time,
            "model_loaded": self._model_loaded,
            "model_path": self.config.get("model_path", str(self.DEFAULT_MODEL_PATH)),
        }

    def _calculate_success_rate(self) -> float:
        """Calculate embedding success rate."""
        total = self.total_embeddings + self.failed_embeddings
        if total == 0:
            return 100.0
        return (self.total_embeddings / total) * 100

    def _update_response_time(self, response_time: float, count: int):
        """Update average response time using moving average."""
        if self.total_embeddings == 0:
            self.average_response_time = response_time
        else:
            n = self.total_embeddings + count
            # Moving average: new_avg = (old_avg * (n-1) + new_value) / n
            total_time = (self.average_response_time * (n - 1)) + (
                response_time * count
            )
            self.average_response_time = total_time / n

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []

        # Check if model is loaded
        if self.model is None and not self._model_loaded:
            status = STATUS_UNHEALTHY
            issues.append("Embedding model not loaded")

        # Check success rate
        success_rate = self._calculate_success_rate()
        if success_rate < 80:  # Less than 80% success rate
            status = STATUS_DEGRADED
            issues.append(f"Low success rate: {success_rate:.1f}%")

        # Check response time
        if self.average_response_time > 5.0:  # More than 5 seconds average (CPU)
            status = STATUS_DEGRADED
            issues.append(f"High response time: {self.average_response_time:.2f}s")

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

    def update_config(self, new_config: EmbeddingConfig | dict[str, Any]) -> bool:
        """Update embedding configuration."""
        try:
            # Convert to dict if needed
            config_dict = {}
            if isinstance(new_config, EmbeddingConfig):
                config_dict = asdict(new_config)
            elif isinstance(new_config, dict):
                config_dict = new_config

            self.config.update(config_dict)
            self.logger.info(f"Embedding configuration updated")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update embedding configuration: {e}")
            return False


# Convenience factory functions


def create_local_embedding_service(
    model_path: str | Path = None,
) -> LocalEmbeddingService:
    """Create a local embedding service with default configuration."""
    config = dict(LocalEmbeddingService._get_default_config())

    if model_path:
        config["model_path"] = model_path

    return LocalEmbeddingService(config=config)


def create_cpu_embedding_service(
    model_path: str | Path = None,
) -> LocalEmbeddingService:
    """Create a CPU-based embedding service."""
    config = dict(LocalEmbeddingService._get_default_config())

    if model_path:
        config["model_path"] = model_path

    return LocalEmbeddingService(config=config)


# Backward compatibility alias
OptimizedLocalEmbeddingService = LocalEmbeddingService
