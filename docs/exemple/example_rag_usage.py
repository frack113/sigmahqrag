#!/usr/bin/env python3
"""
Example usage of the optimized RAG service with ChromaDB.

This demonstrates how to use the RAG service for document storage,
retrieval, and generation with the optimized LLM service.
"""

import asyncio
import sys
import os

# Add the src directory to the path so we can import the services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from nicegui_app.models.llm_service_optimized import create_chat_service
from nicegui_app.models.rag_service_optimized import (
    create_rag_service,
    create_document_rag_service,
    create_chat_rag_service,
)


def test_basic_rag_functionality():
    """Test basic RAG functionality."""
    print("=== Basic RAG Functionality ===\n")

    # Create LLM service
    llm_service = create_chat_service()

    # Create RAG service
    rag_service = create_rag_service(llm_service=llm_service)

    # Sample documents to store
    documents = [
        {
            "id": "doc1",
            "content": "Python is a high-level programming language known for its simplicity and readability. "
            "It was created by Guido van Rossum and first released in 1991. Python supports "
            "multiple programming paradigms including procedural, object-oriented, and functional programming.",
            "metadata": {"category": "programming", "language": "python"},
        },
        {
            "id": "doc2",
            "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms "
            "that can learn from data and make predictions or decisions without being explicitly "
            "programmed. Common techniques include supervised learning, unsupervised learning, "
            "and reinforcement learning.",
            "metadata": {"category": "ai", "topic": "machine_learning"},
        },
        {
            "id": "doc3",
            "content": "Web development involves creating websites and web applications. It includes both "
            "frontend development (what users see) and backend development (server-side logic). "
            "Popular technologies include HTML, CSS, JavaScript, Python, and various frameworks.",
            "metadata": {"category": "web", "topic": "development"},
        },
    ]

    # Store documents
    print("1. Storing documents in vector database:")
    for doc in documents:
        success = rag_service.store_context(
            document_id=doc["id"], text_content=doc["content"], metadata=doc["metadata"]
        )
        print(f"   {doc['id']}: {'Success' if success else 'Failed'}")
    print()

    # Test retrieval
    print("2. Testing document retrieval:")
    test_queries = [
        "What is Python programming?",
        "How does machine learning work?",
        "What technologies are used in web development?",
    ]

    for query in test_queries:
        print(f"   Query: {query}")
        relevant_docs, metadata = rag_service.retrieve_context(
            query=query, n_results=2, min_relevance_score=0.1
        )

        if relevant_docs:
            print(f"   Retrieved {len(relevant_docs)} relevant documents")
            for i, (doc, meta) in enumerate(zip(relevant_docs, metadata)):
                print(f"     Doc {i+1}: {doc[:100]}...")
                print(f"     Similarity: {meta.get('similarity_score', 'N/A')}")
        else:
            print("   No relevant documents found")
        print()

    # Test RAG generation
    print("3. Testing RAG generation:")
    rag_query = "What is Python and how is it used in programming?"
    print(f"   Query: {rag_query}")

    response = asyncio.run(
        rag_service.generate_rag_response(
            query=rag_query, n_results=2, min_relevance_score=0.1
        )
    )

    print(
        f"   Response: {response[:200]}..."
        if len(response) > 200
        else f"   Response: {response}"
    )
    print()

    # Get statistics
    print("4. RAG service statistics:")
    stats = rag_service.get_context_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Cleanup
    rag_service.cleanup()
    llm_service.cleanup()


async def test_streaming_rag():
    """Test streaming RAG functionality."""
    print("=== Streaming RAG Functionality ===\n")

    # Create services
    llm_service = create_chat_service()
    rag_service = create_rag_service(llm_service=llm_service)

    # Store a document for streaming test
    document = {
        "id": "streaming_doc",
        "content": "Streaming responses in RAG systems provide real-time interaction capabilities. "
        "This allows users to see responses as they are generated, improving the user experience "
        "especially for longer responses. The system retrieves relevant context and generates "
        "responses incrementally, yielding chunks as they become available.",
        "metadata": {"category": "streaming", "topic": "rag"},
    }

    rag_service.store_context(
        document_id=document["id"],
        text_content=document["content"],
        metadata=document["metadata"],
    )

    print("1. Testing streaming RAG response:")
    query = "How do streaming responses work in RAG systems?"
    print(f"   Query: {query}")
    print("   Response:")

    # Generate streaming response
    response_parts = []
    async for chunk in rag_service.generate_streaming_rag_response(
        query=query, n_results=1, min_relevance_score=0.1
    ):
        print(chunk, end="", flush=True)
        response_parts.append(chunk)

    print("\n")

    # Test cache functionality
    print("2. Testing cache functionality:")
    cache_stats = rag_service.get_cache_stats()
    print(f"   Cache entries: {cache_stats['total_entries']}")
    print(f"   Valid entries: {cache_stats['valid_entries']}")
    print()

    # Cleanup
    rag_service.cleanup()
    llm_service.cleanup()


def test_specialized_rag_services():
    """Test specialized RAG service configurations."""
    print("=== Specialized RAG Services ===\n")

    # Create LLM service
    llm_service = create_chat_service()

    # 1. Document RAG Service (for long documents)
    print("1. Document RAG Service (optimized for long documents):")
    doc_rag_service = create_document_rag_service(llm_service=llm_service)

    long_document = {
        "id": "long_doc",
        "content": "This is a very long document about advanced programming concepts. "
        * 20
        + "It covers topics like algorithms, data structures, design patterns, and software architecture. "
        * 10
        + "The document is designed to test the RAG service's ability to handle large chunks of text efficiently.",
        "metadata": {"category": "programming", "type": "document"},
    }

    success = doc_rag_service.store_context(
        document_id=long_document["id"],
        text_content=long_document["content"],
        metadata=long_document["metadata"],
    )
    print(f"   Document storage: {'Success' if success else 'Failed'}")

    # Test retrieval with larger chunks
    relevant_docs, metadata = doc_rag_service.retrieve_context(
        query="What topics are covered in this document?",
        n_results=1,
        min_relevance_score=0.05,
    )
    print(f"   Retrieved documents: {len(relevant_docs)}")
    doc_rag_service.cleanup()
    print()

    # 2. Chat RAG Service (for conversational context)
    print("2. Chat RAG Service (optimized for chat applications):")
    chat_rag_service = create_chat_rag_service(llm_service=llm_service)

    chat_context = {
        "id": "chat_context",
        "content": "User preferences: prefers concise answers, likes technical details, "
        "interested in programming and AI topics. Previous conversation topics "
        "included Python programming, machine learning basics, and web development frameworks.",
        "metadata": {"category": "chat", "user_id": "test_user"},
    }

    success = chat_rag_service.store_context(
        document_id=chat_context["id"],
        text_content=chat_context["content"],
        metadata=chat_context["metadata"],
    )
    print(f"   Chat context storage: {'Success' if success else 'Failed'}")

    # Test retrieval with smaller chunks for chat
    relevant_docs, metadata = chat_rag_service.retrieve_context(
        query="What are the user's preferences?", n_results=1, min_relevance_score=0.1
    )
    print(f"   Retrieved context: {len(relevant_docs)}")
    chat_rag_service.cleanup()
    print()

    # Cleanup
    llm_service.cleanup()


def main():
    """Main example function."""
    print("=== Optimized RAG Service Examples ===\n")

    # Test basic functionality
    test_basic_rag_functionality()

    # Test streaming functionality
    asyncio.run(test_streaming_rag())

    # Test specialized services
    test_specialized_rag_services()

    print("=== All RAG examples completed ===")


if __name__ == "__main__":
    main()
