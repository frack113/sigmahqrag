# src.models package - Deprecated Services

# The following services have been deprecated in favor of more modular architecture:
# 
# OLD LOCATION                          | NEW LOCATION                                      | PURPOSE
# -------------------------------------|---------------------------------------------------|------------------
# models/llm_service.py                | core/llm_service.py                               | LLM service
# models/chat_history_service.py       | core/chat_service.py                              | Chat history
# models/config_service.py             | application/config_manager.py                     | Configuration
# models/data_service.py               | infrastructure/database_setup.py                 | Data access
# models/repository_service.py         | infrastructure/database_setup.py                 | Repository pattern
# models/logging_service.py            | (Use Python's built-in logging module)            | Logging

# Deprecated services - kept for backward compatibility only:
from .llm_service import LLMService, create_llm_service, get_llm_service
from .chat_history_service import ChatHistoryService
from .config_service import ConfigService
from .data_service import DataService
from .repository_service import RepositoryService
from .logging_service import LoggingService

__all__ = [
    # Deprecated services
    "LLMService",
    "create_llm_service", 
    "get_llm_service",
    "ChatHistoryService",
    "ConfigService",
    "DataService",
    "RepositoryService",
    "LoggingService",
]

# Use these imports instead for new code:
"""
from src.core.chat_service import ChatService
from src.core.llm_service import LLMService
from src.application.config_manager import ConfigManager
from src.infrastructure.database_setup import DatabaseSetup
from src.core.rag_service import RAGService
import logging
"""