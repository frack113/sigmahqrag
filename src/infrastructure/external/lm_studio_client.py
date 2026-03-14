"""
LM Studio Client - Native Gradio Integration

Uses simple methods without async wrappers:
- Direct requests usage with retry handling
- Simple streaming via synchronous generators
- No asyncio overhead needed (Gradio queue=True handles async)
"""

import json
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LMStudioStats:
    """Statistics for LM Studio client."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_completions: int = 0
    total_embeddings: int = 0
    average_response_time: float = 0.0


class LMStudioClient:
    """
    Simplified LM Studio API client for local LLM operations.

    Features:
    - Text completion (streaming and non-streaming)
    - Embedding generation
    - Model management
    - Simple error handling with built-in retry logic
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        timeout: int = 30,
        max_retries: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ):
        """Initialize the LM Studio client."""
        # Configuration
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Statistics
        self.stats = LMStudioStats()

        # Default model
        self.model = "qwen2.5-7b-instruct"

        # Tracking for response time calculation
        self._last_request_start: float | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get headers for LM Studio API requests."""
        return {
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the LM Studio API with retry logic."""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                headers = self._get_headers()

                if method.upper() == "GET":
                    response = requests.get(
                        url, headers=headers, params=params, timeout=self.timeout
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        url, headers=headers, json=data, timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                self.stats.total_requests += 1

                if response.status_code == 200:
                    self.stats.successful_requests += 1

                    # Calculate and update average response time
                    response_time = time.time() - (
                        self._last_request_start or time.time()
                    )
                    self._update_average_response_time(response_time)

                    if response.content:
                        return response.json()
                    return {}
                else:
                    self.stats.failed_requests += 1
                    raise Exception(f"HTTP {response.status_code}")

            except requests.exceptions.RequestException:
                self.stats.failed_requests += 1

                if attempt == self.max_retries - 1:
                    raise

                time.sleep(1.0 * (2**attempt))  # Exponential backoff

        return {}

    def _update_average_response_time(self, response_time: float) -> None:
        """Update average response time (moving average)."""
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

        self._last_request_start = time.time()

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
    ) -> Generator[str, None, None] | dict[str, Any]:
        """
        Chat completion using the chat API.

        Gradio handles async automatically with queue=True, so we use
        synchronous generators for streaming instead of async generators.

        Args:
            messages: List of message dictionaries with role and content
            model: Model ID (optional)
            max_tokens: Max tokens (optional)
            temperature: Temperature (optional)
            stream: Whether to stream response

        Returns:
            Dict for non-streaming, Generator[str] for streaming
        """
        endpoint = "v1/chat/completions"

        data = {
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
        }

        if model:
            data["model"] = model

        if stream:
            return self._stream_chat_completion(data)

        response = self._make_request("POST", endpoint, data=data)
        self.stats.total_completions += 1

        if response.get("choices"):
            return response["choices"][0].get("message", {})
        return {}

    def _stream_chat_completion(
        self, data: dict[str, Any]
    ) -> Generator[str, None, None]:
        """Stream chat completion responses synchronously."""
        endpoint = "v1/chat/completions"

        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()

        response = requests.post(
            url, headers=headers, json=data, timeout=self.timeout, stream=True
        )

        self.stats.total_completions += 1
        self.stats.successful_requests += 1

        # Process streaming response synchronously (Gradio handles async)
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
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

    def generate_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """Generate text embedding."""
        endpoint = "v1/embeddings"

        data = {
            "input": text,
        }

        if model:
            data["model"] = model

        response = self._make_request("POST", endpoint, data=data)

        self.stats.total_embeddings += 1

        embeddings_data = response.get("data", [])
        if embeddings_data:
            return embeddings_data[0].get("embedding", [])
        return []

    def is_server_running(self) -> bool:
        """Check if LM Studio server is running."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> list[dict[str, Any]]:
        """Get available models from the server."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                return response.json().get("data", [])
        except Exception as e:
            print(f"Failed to get models: {e}")

        # Return default model if server is unavailable
        return [{"id": self.model, "model": f"qwen/{self.model}"}]

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "total_completions": self.stats.total_completions,
            "total_embeddings": self.stats.total_embeddings,
            "average_response_time": self.stats.average_response_time,
        }


def create_lm_studio_client(
    base_url: str = "http://localhost:1234",
) -> LMStudioClient:
    """Create an LM Studio client with default configuration."""
    return LMStudioClient(base_url=base_url)
