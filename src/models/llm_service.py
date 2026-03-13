# This file has been deprecated.
# LLMService functionality has been moved to src/core/llm_service.py
# Keep for backward compatibility only
from src.core.llm_service import LLMService, create_llm_service, get_llm_service

__all__ = ["LLMService", "create_llm_service", "get_llm_service"]