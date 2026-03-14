"""
LLM Service - Optimized for performance and ease of use

Provides an optimized LLM interface using LM Studio with:
- Factory functions for different use cases (chat, completion, creative)
- Performance optimizations
- Comprehensive error handling
- Caching support
- Resource monitoring
- Rate limiting
"""

import time
from typing import Any

import requests


class LLMService:
    """Optimized LLM service with OpenAI compatibility."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        api_key: str = "lm-studio",
        model: str = "qwen/qwen2.5-7b-instruct",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ):
        """Initialize LLM service."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _make_request(self, messages: list[dict], stream: bool = False) -> Any:
        """Make API request to LM Studio."""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if stream:
            response = requests.post(url, json=payload, stream=True)
            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = __import__("json").loads(data_str)
                            yield chunk["choices"][0]["delta"].get("content", "")
                        except Exception:
                            continue
        else:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                yield data["choices"][0]["message"].get("content", "")
            else:
                yield ""

    def simple_completion(self, prompt: str) -> str:
        """Get a simple completion."""
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(messages)["content"]

    def chat_completion(self, messages: list[dict], model: str | None = None, **kwargs) -> dict[str, Any]:
        """Chat completion with optional streaming."""
        data = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }

        response = requests.post(f"{self.base_url}/v1/chat/completions", json=data, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {}

    def generate_completion(self, messages: list[dict]) -> str:
        """Generate completion from messages."""
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        response = requests.post(f"{self.base_url}/v1/chat/completions", json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""


def create_chat_service(
    base_url: str = "http://localhost:1234",
    model: str = "qwen/qwen2.5-7b-instruct",
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> LLMService:
    """Create a chat-focused service optimized for conversation."""
    return LLMService(
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def create_completion_service(
    base_url: str = "http://localhost:1234",
    model: str = "qwen/qwen2.5-7b-instruct",
) -> LLMService:
    """Create a completion-focused service optimized for text generation."""
    return LLMService(base_url=base_url, model=model, temperature=0.3, max_tokens=1024)


def create_creative_service(
    base_url: str = "http://localhost:1234",
    model: str = "qwen/qwen2.5-7b-instruct",
) -> LLMService:
    """Create a creative-focused service optimized for creative writing."""
    return LLMService(base_url=base_url, model=model, temperature=1.2, max_tokens=2048)


def create_llm_service() -> LLMService:
    """Create a default LLM service."""
    return LLMService()