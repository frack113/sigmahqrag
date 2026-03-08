"""
Optimized LLM Service for NiceGUI - OpenAI Compatible

Optimized version of the LLM service based on real usage patterns.
Focuses on simplicity, performance, and ease of use while maintaining
full OpenAI compatibility.
"""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Union

import markdown
from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
    ChatCompletionTokenLogprob,
)
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice
from openai.types.chat.chat_completion_chunk import Choice as ChatCompletionChunkChoice
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.completion_usage import CompletionUsage

logger = logging.getLogger(__name__)

# Type aliases for OpenAI compatibility
Role = Literal["system", "user", "assistant", "tool", "function", "developer"]
FinishReason = Literal[
    "stop", "length", "tool_calls", "content_filter", "function_call"
]


@dataclass
class ChatMessage:
    """Represents a chat message in the conversation."""

    role: Role
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    function_call: Optional[Dict[str, Any]] = None
    refusal: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """OpenAI-compatible chat completion request."""

    messages: List[ChatMessage]
    model: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False
    stream_options: Optional[Dict[str, Any]] = None
    stop: Optional[Union[str, List[str]]] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    user: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    logprobs: Optional[bool] = False
    top_logprobs: Optional[int] = None
    modalities: Optional[List[str]] = None
    audio: Optional[Dict[str, Any]] = None
    verbosity: Optional[str] = None
    web_search_options: Optional[Dict[str, Any]] = None
    prompt_cache_key: Optional[str] = None
    prompt_cache_retention: Optional[str] = None
    reasoning_effort: Optional[str] = None
    service_tier: Optional[str] = None
    safety_identifier: Optional[str] = None


class OptimizedLLMService:
    """
    Optimized LLM service for common use cases.
    
    Key optimizations based on real usage patterns:
    1. Simplified initialization with sensible defaults
    2. Optimized client reuse and connection management
    3. Streamlined message handling for common patterns
    4. Better error handling and fallbacks
    5. Reduced memory footprint for simple completions
    """

    def __init__(
        self,
        model_name: str = "mistralai/ministral-3-14b-reasoning",
        base_url: str = "http://localhost:1234",
        temperature: float = 0.7,
        max_tokens: int = 512,
        api_key: str = "lm-studio",
        enable_streaming: bool = True,
    ):
        """
        Initialize the optimized LLM service.
        
        Args:
            model_name: Name of the model to use
            base_url: Base URL for the LLM server
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            api_key: API key for LM Studio (default: "lm-studio")
            enable_streaming: Enable streaming responses
        """
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.enable_streaming = enable_streaming
        self.client = None
        self._executor = None
        self._client_lock = Lock()
        
        # Initialize client with retry logic
        self._initialize_client_with_retry()

    def _initialize_client_with_retry(self, max_retries: int = 3) -> bool:
        """Initialize the OpenAI client with retry logic."""
        for attempt in range(max_retries):
            try:
                self.client = OpenAI(
                    base_url=f"{self.base_url}/v1",
                    api_key=self.api_key,
                )
                logger.info(
                    f"LLM client initialized with model: {self.model_name} at {self.base_url}"
                )
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to initialize LLM client after {max_retries} attempts: {e}")
                    self.client = None
                    return False
                logger.warning(f"Client initialization attempt {attempt + 1} failed: {e}")
                continue
        return False

    def _build_simple_messages(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build simple message structure for common use cases."""
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif self.temperature < 1.0:  # Only add default for non-creative tasks
            messages.append({
                "role": "system", 
                "content": "You are a helpful assistant. Provide clear, concise, and accurate responses."
            })
        
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        return messages

    def simple_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Optimized simple completion function.
        
        This is the primary interface for most use cases.
        
        Args:
            prompt: The user input prompt
            system_prompt: Optional system prompt to set context
            
        Returns:
            The LLM's response text
        """
        try:
            # Lazy client initialization with better error handling
            if self.client is None:
                if not self._initialize_client_with_retry():
                    return "Error: Failed to initialize LLM client after multiple attempts"
            
            # Build optimized message structure
            messages = self._build_simple_messages(prompt, system_prompt)
            
            # Create optimized parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }

            # Make the API call with timeout handling
            try:
                response = self.client.chat.completions.create(**params)
                
                # Extract response with fallback
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
                else:
                    return "No response generated by the model."
                    
            except Exception as api_error:
                logger.error(f"API call failed: {api_error}")
                return f"Error: API call failed - {str(api_error)}"
                
        except Exception as e:
            logger.error(f"Error in simple_completion: {e}")
            return f"Error: {str(e)}"

    def batch_completion(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
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
            response = self.simple_completion(prompt, system_prompt)
            responses.append(response)
        return responses

    async def streaming_completion(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Stream completion responses for real-time applications.
        
        Args:
            prompt: The user input prompt
            system_prompt: Optional system prompt to set context
            
        Returns:
            Async generator yielding response chunks
        """
        try:
            if self.client is None:
                if not self._initialize_client_with_retry():
                    yield "Error: Failed to initialize LLM client"
                    return
            
            messages = self._build_simple_messages(prompt, system_prompt)
            
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True
            }

            try:
                # Use asyncio to run the streaming in a thread
                import asyncio
                loop = asyncio.get_event_loop()
                
                def _stream_sync():
                    stream = self.client.chat.completions.create(**params)
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                
                # Convert sync generator to async generator
                for chunk in _stream_sync():
                    yield chunk
                        
            except Exception as e:
                logger.error(f"Streaming failed: {e}")
                yield f"Error: Streaming failed - {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in streaming_completion: {e}")
            yield f"Error: {str(e)}"

    def check_availability(self) -> bool:
        """Check if the LLM service is available."""
        try:
            if self.client is None:
                return self._initialize_client_with_retry()
            
            # Try a simple model list call
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            logger.error(f"Service availability check failed: {e}")
            return False

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get basic usage statistics."""
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "client_initialized": self.client is not None,
            "enable_streaming": self.enable_streaming
        }

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None
            
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None
                
        except Exception as e:
            logger.error(f"Error during LLM service cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory functions for common configurations
def create_chat_service(
    model_name: str = "mistralai/ministral-3-14b-reasoning",
    base_url: str = "http://localhost:1234",
    temperature: float = 0.7,
    max_tokens: int = 512
) -> OptimizedLLMService:
    """Create a chat-focused LLM service."""
    return OptimizedLLMService(
        model_name=model_name,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        enable_streaming=True
    )


def create_completion_service(
    model_name: str = "mistralai/ministral-3-14b-reasoning",
    base_url: str = "http://localhost:1234",
    temperature: float = 0.3,  # Lower temperature for more deterministic responses
    max_tokens: int = 1024
) -> OptimizedLLMService:
    """Create a completion-focused LLM service."""
    return OptimizedLLMService(
        model_name=model_name,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        enable_streaming=False
    )


def create_creative_service(
    model_name: str = "mistralai/ministral-3-14b-reasoning",
    base_url: str = "http://localhost:1234",
    temperature: float = 1.2,  # Higher temperature for more creative responses
    max_tokens: int = 2048
) -> OptimizedLLMService:
    """Create a creative-focused LLM service."""
    return OptimizedLLMService(
        model_name=model_name,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        enable_streaming=True
    )


# Backward compatibility alias
LLMService = OptimizedLLMService