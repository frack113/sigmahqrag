"""
LLM Service for SigmaHQ RAG application.

Provides LLM functionality with OpenAI compatibility, optimized for performance
and ease of use. Integrates with the new service architecture.
"""

import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Literal

from openai import OpenAI

from src.shared import (
    DEFAULT_LLM_API_KEY,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_ENABLE_STREAMING,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TEMPERATURE,
    SERVICE_LLM,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    AsyncComponent,
    BaseService,
    CacheService,
    LLMConfig,
    LLMError,
    NetworkError,
    get_cpu_usage,
    get_memory_usage,
)

from src.shared.utils import (
    handle_service_errors,
    rate_limit,
    retry_with_backoff,
)

# Type aliases for OpenAI compatibility
Role = Literal["system", "user", "assistant", "tool", "function", "developer"]
FinishReason = Literal[
    "stop", "length", "tool_calls", "content_filter", "function_call"
]


@dataclass
class LLMStats:
    """Statistics for LLM service."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    average_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class LLMService(BaseService, AsyncComponent):
    """
    LLM service for SigmaHQ RAG application.

    Provides optimized LLM functionality with:
    - OpenAI compatibility
    - Performance optimizations
    - Comprehensive error handling
    - Caching support
    - Resource monitoring
    - Rate limiting
    """

    def __init__(self, config: LLMConfig | None = None):
        """
        Initialize the LLM service.

        Args:
            config: LLM configuration
        """
        BaseService.__init__(self, f"{SERVICE_LLM}.llm_service")
        AsyncComponent.__init__(self)

        # Configuration
        self.config = config or self._get_default_config()

        # Service state
        self.client: OpenAI | None = None
        self._client_lock = Lock()
        self._initialized = False
        self._start_time = datetime.now()

        # Statistics
        self.stats = LLMStats()

        # Caching
        self.cache = CacheService(max_size=1000, default_ttl=3600)

        # Initialize service
        self._initialize_client_with_retry()

    def _get_default_config(self) -> LLMConfig:
        """Get default LLM configuration."""
        return LLMConfig(
            model=DEFAULT_LLM_MODEL,
            base_url=DEFAULT_LLM_BASE_URL,
            api_key=DEFAULT_LLM_API_KEY,
            temperature=DEFAULT_LLM_TEMPERATURE,
            max_tokens=DEFAULT_LLM_MAX_TOKENS,
            enable_streaming=DEFAULT_LLM_ENABLE_STREAMING,
        )

    async def initialize(self) -> bool:
        """
        Initialize the LLM service.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            success = self._initialize_client_with_retry()
            if success:
                self._initialized = True
                self._log_operation("LLM service initialization", True)
                self.logger.info(
                    f"LLM service initialized with model: {self.config['model']}"
                )
            else:
                self._log_operation("LLM service initialization", False)
                self.logger.error("LLM service initialization failed")

            return success
        except Exception as e:
            self._log_operation("LLM service initialization", False, {"error": str(e)})
            self.logger.error(f"LLM service initialization failed: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None

            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

            self._initialized = False
            self._log_operation("LLM service cleanup", True)

        except Exception as e:
            self._log_operation("LLM service cleanup", False, {"error": str(e)})
            self.logger.error(f"Error during LLM service cleanup: {e}")

    def _initialize_client_with_retry(self, max_retries: int = 3) -> bool:
        """Initialize the OpenAI client with retry logic."""
        for attempt in range(max_retries):
            try:
                self.client = OpenAI(
                    base_url=f"{self.config['base_url']}/v1",
                    api_key=self.config["api_key"],
                )
                self.logger.info(
                    f"LLM client initialized with model: {self.config['model']} "
                    f"at {self.config['base_url']}"
                )
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        f"Failed to initialize LLM client after {max_retries} attempts: {e}"
                    )
                    self.client = None
                    return False
                self.logger.warning(
                    f"Client initialization attempt {attempt + 1} failed: {e}"
                )
                continue
        return False

    def _build_simple_messages(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict[str, str]]:
        """Build simple message structure for common use cases."""
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif (
            self.config["temperature"] < 1.0
        ):  # Only add default for non-creative tasks
            messages.append(
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Provide clear, concise, and accurate responses.",
                }
            )

        # Add user message
        messages.append({"role": "user", "content": prompt})

        return messages

    @handle_service_errors(
        error_types=[NetworkError, LLMError], default_message="LLM completion failed"
    )
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    @rate_limit(max_calls=100, time_window=60)  # 100 calls per minute
    async def simple_completion(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        """
        Optimized simple completion function.

        This is the primary interface for most use cases.

        Args:
            prompt: The user input prompt
            system_prompt: Optional system prompt to set context

        Returns:
            The LLM's response text
        """
        start_time = time.time()

        try:
            # Check cache first
            cache_key = self._generate_cache_key(
                "simple_completion", prompt, system_prompt
            )
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                self.stats.total_requests += 1
                self.stats.successful_requests += 1
                self._update_stats(start_time)
                self.logger.info("LLM completion served from cache")
                return cached_result

            # Lazy client initialization with better error handling
            if self.client is None:
                if not self._initialize_client_with_retry():
                    error_msg = (
                        "Failed to initialize LLM client after multiple attempts"
                    )
                    self._update_stats(start_time, error=error_msg)
                    return error_msg

            # Build optimized message structure
            messages = self._build_simple_messages(prompt, system_prompt)

            # Create optimized parameters
            params = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_tokens"],
                "stream": False,
            }

            # Make the API call with timeout handling
            try:
                response = await self.run_in_executor(
                    self.client.chat.completions.create, **params
                )

                # Extract response with fallback
                if response.choices and response.choices[0].message.content:
                    result = response.choices[0].message.content.strip()
                else:
                    result = "No response generated by the model."

                # Cache the result
                await self.cache.set(cache_key, result, ttl=1800)  # 30 minutes

                self.stats.total_requests += 1
                self.stats.successful_requests += 1
                self.stats.total_tokens_used += (
                    response.usage.total_tokens if response.usage else 0
                )
                self._update_stats(start_time)

                return result

            except Exception as api_error:
                error_msg = f"API call failed: {str(api_error)}"
                self._update_stats(start_time, error=error_msg)
                raise NetworkError(error_msg)

        except Exception as e:
            error_msg = f"Error in simple_completion: {str(e)}"
            self._update_stats(start_time, error=error_msg)
            raise LLMError(error_msg)

    @handle_service_errors(
        error_types=[NetworkError, LLMError],
        default_message="LLM batch completion failed",
    )
    async def batch_completion(
        self, prompts: list[str], system_prompt: str | None = None
    ) -> list[str]:
        """
        Process multiple prompts efficiently.

        Args:
            prompts: List of prompts to process
            system_prompt: Optional system prompt for all prompts

        Returns:
            List of responses corresponding to each prompt
        """
        responses = []
        for prompt in prompts:
            response = await self.simple_completion(prompt, system_prompt)
            responses.append(response)
        return responses

    @handle_service_errors(
        error_types=[NetworkError, LLMError], default_message="LLM streaming failed"
    )
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    async def streaming_completion(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion responses for real-time applications.

        Args:
            prompt: The user input prompt
            system_prompt: Optional system prompt to set context

        Yields:
            Response chunks for streaming
        """
        start_time = time.time()

        try:
            if self.client is None:
                if not self._initialize_client_with_retry():
                    yield "Error: Failed to initialize LLM client"
                    return

            messages = self._build_simple_messages(prompt, system_prompt)

            params = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": self.config["temperature"],
                "max_tokens": self.config["max_tokens"],
                "stream": True,
            }

            try:
                # Create async generator for streaming
                async def _stream_async():
                    stream = self.client.chat.completions.create(**params)
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                # Run async generator in executor
                loop = asyncio.get_event_loop()
                sync_generator = _stream_async()

                # Process chunks one by one
                async for chunk in sync_generator:
                    yield chunk

                self.stats.total_requests += 1
                self.stats.successful_requests += 1
                self._update_stats(start_time)

            except Exception as e:
                error_msg = f"Streaming failed: {str(e)}"
                self._update_stats(start_time, error=error_msg)
                yield f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Error in streaming_completion: {str(e)}"
            self._update_stats(start_time, error=error_msg)
            yield f"Error: {error_msg}"

    def check_availability(self) -> bool:
        """Check if the LLM service is available."""
        try:
            if self.client is None:
                return self._initialize_client_with_retry()

            # Try a simple model list call
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            self.logger.error(f"Service availability check failed: {e}")
            return False

    def get_usage_stats(self) -> dict[str, Any]:
        """Get basic usage statistics."""
        return {
            "model_name": self.config["model"],
            "base_url": self.config["base_url"],
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_tokens"],
            "client_initialized": self.client is not None,
            "enable_streaming": self.config["enable_streaming"],
            "service_stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "total_tokens_used": self.stats.total_tokens_used,
                "average_response_time": self.stats.average_response_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": self.stats.uptime_seconds,
            },
            "cache_stats": self.cache.get_stats(),
        }

    def _update_stats(self, start_time: float, error: str | None = None) -> None:
        """Update service statistics."""
        end_time = time.time()
        response_time = end_time - start_time

        # Update response time (moving average)
        if self.stats.total_requests > 0:
            self.stats.average_response_time = (
                (self.stats.average_response_time * (self.stats.total_requests - 1))
                + response_time
            ) / self.stats.total_requests
        else:
            self.stats.average_response_time = response_time

        # Update memory and CPU usage
        memory_info = get_memory_usage()
        self.stats.memory_usage_mb = memory_info.get("rss_mb", 0)
        self.stats.cpu_usage_percent = get_cpu_usage()

        # Update uptime
        self.stats.uptime_seconds = (datetime.now() - self._start_time).total_seconds()

        # Update error stats
        if error:
            self.stats.failed_requests += 1
            self.stats.last_error = error
        else:
            self.stats.successful_requests += 1

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []

        # Check client availability
        if self.client is None:
            status = STATUS_UNHEALTHY
            issues.append("LLM client not initialized")

        # Check error rate
        if self.stats.total_requests > 0:
            error_rate = self.stats.failed_requests / self.stats.total_requests
            if error_rate > 0.1:  # More than 10% error rate
                status = STATUS_DEGRADED
                issues.append(f"High error rate: {error_rate:.2%}")

        # Check response time
        if self.stats.average_response_time > 30.0:  # More than 30 seconds average
            status = STATUS_DEGRADED
            issues.append(
                f"High response time: {self.stats.average_response_time:.2f}s"
            )

        # Check memory usage
        if self.stats.memory_usage_mb > 1024.0:  # More than 1GB
            status = STATUS_DEGRADED
            issues.append(f"High memory usage: {self.stats.memory_usage_mb:.2f}MB")

        return {
            "service": SERVICE_LLM,
            "status": status,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
            "stats": self.get_usage_stats(),
        }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        self.logger.info("LLM cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()

    def update_config(self, new_config: LLMConfig) -> bool:
        """Update LLM configuration."""
        try:
            self.config = new_config
            # Reinitialize client with new config
            if not self._initialize_client_with_retry():
                raise LLMError("Failed to reinitialize LLM client with new config")

            self.logger.info(f"LLM configuration updated: {new_config['model']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update LLM configuration: {e}")
            return False


# Convenience factory functions for common configurations
def create_chat_service(
    config: LLMConfig | None = None,
) -> LLMService:
    """Create a chat-focused LLM service."""
    default_config = LLMConfig(
        model=DEFAULT_LLM_MODEL,
        base_url=DEFAULT_LLM_BASE_URL,
        api_key=DEFAULT_LLM_API_KEY,
        temperature=0.7,
        max_tokens=512,
        enable_streaming=True,
    )

    if config:
        default_config.update(config)

    return LLMService(default_config)


def create_completion_service(
    config: LLMConfig | None = None,
) -> LLMService:
    """Create a completion-focused LLM service."""
    default_config = LLMConfig(
        model=DEFAULT_LLM_MODEL,
        base_url=DEFAULT_LLM_BASE_URL,
        api_key=DEFAULT_LLM_API_KEY,
        temperature=0.3,  # Lower temperature for more deterministic responses
        max_tokens=1024,
        enable_streaming=False,
    )

    if config:
        default_config.update(config)

    return LLMService(default_config)


def create_creative_service(
    config: LLMConfig | None = None,
) -> LLMService:
    """Create a creative-focused LLM service."""
    default_config = LLMConfig(
        model=DEFAULT_LLM_MODEL,
        base_url=DEFAULT_LLM_BASE_URL,
        api_key=DEFAULT_LLM_API_KEY,
        temperature=1.2,  # Higher temperature for more creative responses
        max_tokens=2048,
        enable_streaming=True,
    )

    if config:
        default_config.update(config)

    return LLMService(default_config)


# Backward compatibility alias
OptimizedLLMService = LLMService
