"""
LM Studio Client for SigmaHQ RAG application.

Provides LM Studio API integration for local LLM operations.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import requests

from src.shared import (
    DEFAULT_LM_STUDIO_BASE_URL,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    BaseService,
    NetworkError,
    ServiceError,
)
from src.shared.constants import SERVICE_LM_STUDIO


@dataclass
class LMStudioStats:
    """Statistics for LM Studio client."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_completions: int = 0
    total_embeddings: int = 0
    average_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class LMStudioClient(BaseService):
    """
    LM Studio API client for local LLM operations.

    Features:
    - Text completion
    - Embedding generation
    - Model management
    - Health monitoring
    - Error handling
    """

    def __init__(
        self,
        base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the LM Studio client.

        Args:
            base_url: LM Studio API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        BaseService.__init__(self, f"{SERVICE_LM_STUDIO}.lm_studio_client")

        # Configuration
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        # Statistics
        self.stats = LMStudioStats()
        self._start_time = time.time()

    def _get_headers(self) -> dict[str, str]:
        """Get headers for LM Studio API requests."""
        return {
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a request to the LM Studio API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: Query parameters

        Returns:
            Response data
        """
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                headers = self._get_headers()

                # Make request
                if method.upper() == "GET":
                    response = requests.get(
                        url, headers=headers, params=params, timeout=self.timeout
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        url, headers=headers, json=data, timeout=self.timeout
                    )
                elif method.upper() == "PUT":
                    response = requests.put(
                        url, headers=headers, json=data, timeout=self.timeout
                    )
                elif method.upper() == "DELETE":
                    response = requests.delete(
                        url, headers=headers, timeout=self.timeout
                    )
                else:
                    raise ServiceError(f"Unsupported HTTP method: {method}")

                # Update statistics
                self.stats.total_requests += 1

                # Handle response
                response.raise_for_status()
                self.stats.successful_requests += 1

                response_time = time.time() - start_time

                # Update average response time (moving average)
                if self.stats.successful_requests > 1:
                    self.stats.average_response_time = (
                        (
                            self.stats.average_response_time
                            * (self.stats.successful_requests - 1)
                        )
                        + response_time
                    ) / self.stats.successful_requests
                else:
                    self.stats.average_response_time = response_time

                if response.content:
                    return response.json()
                else:
                    return {}

            except requests.exceptions.RequestException as e:
                self.stats.failed_requests += 1
                self.stats.last_error = str(e)

                if attempt == self.max_retries - 1:  # Last attempt
                    self.logger.error(
                        f"LM Studio API request failed after {self.max_retries} attempts: {e}"
                    )
                    raise NetworkError(f"LM Studio API request failed: {str(e)}")

                # Wait before retry
                await asyncio.sleep(1.0 * (2**attempt))  # Exponential backoff

            except Exception as e:
                self.stats.failed_requests += 1
                self.stats.last_error = str(e)
                self.logger.error(f"LM Studio API error: {e}")
                raise ServiceError(f"LM Studio API error: {str(e)}")

    async def get_models(self) -> list[dict[str, Any]]:
        """
        Get available models.

        Returns:
            List of available models
        """
        endpoint = "v1/models"
        response = await self._make_request("GET", endpoint)

        return response.get("data", [])

    async def get_model_info(self, model_id: str) -> dict[str, Any]:
        """
        Get model information.

        Args:
            model_id: Model identifier

        Returns:
            Model information
        """
        endpoint = f"v1/models/{model_id}"
        return await self._make_request("GET", endpoint)

    async def generate_completion(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stop: list[str] | None = None,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            model: Model to use (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop: Stop sequences

        Returns:
            Generated text
        """
        endpoint = "v1/completions"

        data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        if model:
            data["model"] = model

        if stop:
            data["stop"] = stop

        response = await self._make_request("POST", endpoint, data=data)

        self.stats.total_completions += 1

        choices = response.get("choices", [])
        if choices:
            return choices[0].get("text", "")
        else:
            return ""

    async def generate_streaming_completion(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stop: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming text completion.

        Args:
            prompt: Input prompt
            model: Model to use (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop: Stop sequences

        Yields:
            Response chunks for streaming
        """
        endpoint = "v1/completions"

        data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }

        if model:
            data["model"] = model

        if stop:
            data["stop"] = stop

        try:
            url = f"{self.base_url}/{endpoint}"
            headers = self._get_headers()

            response = requests.post(
                url, headers=headers, json=data, timeout=self.timeout, stream=True
            )
            response.raise_for_status()

            self.stats.total_completions += 1
            self.stats.successful_requests += 1

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            self.stats.failed_requests += 1
            self.stats.last_error = str(e)
            self.logger.error(f"LM Studio streaming completion failed: {e}")
            raise ServiceError(f"Streaming completion failed: {str(e)}")

    async def generate_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """
        Generate text embedding.

        Args:
            text: Input text
            model: Model to use (optional)

        Returns:
            Embedding vector
        """
        endpoint = "v1/embeddings"

        data = {
            "input": text,
        }

        if model:
            data["model"] = model

        response = await self._make_request("POST", endpoint, data=data)

        self.stats.total_embeddings += 1

        data_list = response.get("data", [])
        if data_list:
            return data_list[0].get("embedding", [])
        else:
            return []

    async def generate_multiple_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            model: Model to use (optional)

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for text in texts:
            try:
                embedding = await self.generate_embedding(text, model)
                embeddings.append(embedding)
            except Exception as e:
                self.logger.error(f"Failed to generate embedding for text: {e}")
                embeddings.append([])

        return embeddings

    async def get_model_usage(self) -> dict[str, Any]:
        """
        Get model usage statistics.

        Returns:
            Usage statistics
        """
        try:
            # Try to get usage from the server if available
            endpoint = "v1/usage"
            return await self._make_request("GET", endpoint)

        except Exception as e:
            self.logger.warning(f"Could not get model usage: {e}")
            return {}

    def is_server_running(self) -> bool:
        """
        Check if LM Studio server is running.

        Returns:
            True if server is running
        """
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []

        # Check server availability
        if not self.is_server_running():
            status = STATUS_UNHEALTHY
            issues.append("LM Studio server not running")

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

        return {
            "service": SERVICE_LM_STUDIO,
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "total_completions": self.stats.total_completions,
                "total_embeddings": self.stats.total_embeddings,
                "average_response_time": self.stats.average_response_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "server_running": self.is_server_running(),
            "config": {
                "base_url": self.base_url,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config": {
                "base_url": self.base_url,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
            "stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "total_completions": self.stats.total_completions,
                "total_embeddings": self.stats.total_embeddings,
                "average_response_time": self.stats.average_response_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "server_running": self.is_server_running(),
            "model_usage": self.get_model_usage(),
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("LM Studio client cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during LM Studio client cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory function
def create_lm_studio_client(
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    timeout: int = 30,
    max_retries: int = 3,
) -> LMStudioClient:
    """Create an LM Studio client with default configuration."""
    return LMStudioClient(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
    )
