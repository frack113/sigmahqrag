#!/usr/bin/env python3
"""
Example usage of the optimized LLM service.

This demonstrates the improved service with better performance and ease of use.
"""

import sys
import os
import asyncio

# Add the src directory to the path so we can import the LLM service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from nicegui_app.models.llm_service_optimized import (
    OptimizedLLMService,
    create_chat_service,
    create_completion_service,
    create_creative_service
)


def test_basic_usage():
    """Test basic usage with the optimized service."""
    print("=== Basic Usage with Optimized Service ===\n")
    
    # Create service with factory function
    llm_service = create_chat_service()
    
    # Test basic completion
    print("1. Basic completion:")
    response = llm_service.simple_completion("What is 2 + 2?")
    print(f"Response: {response}")
    print()
    
    # Test with custom system prompt
    print("2. With custom system prompt:")
    response = llm_service.simple_completion(
        "Explain gravity",
        "You are a physics teacher explaining concepts to beginners."
    )
    print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
    print()
    
    # Check service availability
    print("3. Service availability:")
    available = llm_service.check_availability()
    print(f"Service available: {available}")
    print()
    
    # Get usage statistics
    print("4. Usage statistics:")
    stats = llm_service.get_usage_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    llm_service.cleanup()


def test_batch_processing():
    """Test batch processing capabilities."""
    print("=== Batch Processing ===\n")
    
    llm_service = create_completion_service()
    
    # Test batch completion
    prompts = [
        "What is the capital of France?",
        "What is 5 + 7?",
        "Write a one-sentence summary of Python programming."
    ]
    
    print("Processing batch of prompts:")
    responses = llm_service.batch_completion(prompts)
    
    for i, (prompt, response) in enumerate(zip(prompts, responses), 1):
        print(f"{i}. Prompt: {prompt}")
        print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
        print()
    
    llm_service.cleanup()


async def test_streaming():
    """Test streaming capabilities."""
    print("=== Streaming Completion ===\n")
    
    llm_service = create_creative_service()
    
    print("Streaming response for creative task:")
    print("Prompt: Write a short poem about programming")
    print("Response:")
    
    # Stream the response
    async for chunk in llm_service.streaming_completion(
        "Write a short poem about programming",
        "You are a creative writer"
    ):
        print(chunk, end="", flush=True)
    
    print("\n")
    llm_service.cleanup()


def test_service_variants():
    """Test different service variants."""
    print("=== Service Variants ===\n")
    
    # Chat service (medium temperature, streaming enabled)
    chat_service = create_chat_service(temperature=0.7, max_tokens=512)
    print("1. Chat Service (temperature=0.7):")
    response = chat_service.simple_completion("Tell me a joke")
    print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
    chat_service.cleanup()
    print()
    
    # Completion service (low temperature, deterministic)
    completion_service = create_completion_service(temperature=0.3, max_tokens=1024)
    print("2. Completion Service (temperature=0.3):")
    response = completion_service.simple_completion("Explain the difference between Python and JavaScript")
    print(f"   Response: {response[:150]}..." if len(response) > 150 else f"   Response: {response}")
    completion_service.cleanup()
    print()
    
    # Creative service (high temperature, creative)
    creative_service = create_creative_service(temperature=1.2, max_tokens=2048)
    print("3. Creative Service (temperature=1.2):")
    response = creative_service.simple_completion("Write a fantasy story about a dragon programmer")
    print(f"   Response: {response[:200]}..." if len(response) > 200 else f"   Response: {response}")
    creative_service.cleanup()
    print()


def main():
    """Main example function."""
    print("=== Optimized LLM Service Examples ===\n")
    
    # Test basic usage
    test_basic_usage()
    
    # Test batch processing
    test_batch_processing()
    
    # Test streaming (async)
    asyncio.run(test_streaming())
    
    # Test different service variants
    test_service_variants()
    
    print("=== All examples completed ===")


if __name__ == "__main__":
    main()