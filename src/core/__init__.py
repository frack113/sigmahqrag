"""
Core services for SigmaHQ RAG application.

This module provides the core business logic services including LLM, RAG, and Chat services.
"""

# Export core services
from .chat_service import ChatService, ChatStats
from .chat_service import create_chat_service as create_chat_service_instance

# Export dataclasses
from .llm_service import (
    LLMService,
    LLMStats,
    create_chat_service,
    create_completion_service,
    create_creative_service,
)
from .rag_service import (
    RAGService,
    RAGStats,
    create_chat_rag_service,
    create_document_rag_service,
    create_rag_service,
)

__all__ = [
    # LLM Service
    "LLMService",
    "LLMStats",
    "create_chat_service",
    "create_completion_service",
    "create_creative_service",
    # RAG Service
    "RAGService",
    "RAGStats",
    "create_rag_service",
    "create_document_rag_service",
    "create_chat_rag_service",
    # Chat Service
    "ChatService",
    "ChatStats",
    "create_chat_service_instance",
]
