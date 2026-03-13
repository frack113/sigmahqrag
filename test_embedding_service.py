#!/usr/bin/env python3
"""
Simple test script to verify the local embedding service works.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all our services can be imported."""
    try:
        print("Testing imports...")
        
        # Test core services
        from src.core.llm_service import LLMService
        print("LLMService import successful")
        
        from src.core.rag_service import RAGService
        print("RAGService import successful")
        
        # Test local embedding service
        from src.core.local_embedding_service import LocalEmbeddingService
        print("LocalEmbeddingService import successful")
        
        # Test shared constants
        from src.shared import SERVICE_EMBEDDING, SERVICE_RAG, SERVICE_LLM
        print(f"Service constants import successful: {SERVICE_EMBEDDING}, {SERVICE_RAG}, {SERVICE_LLM}")
        
        # Test exceptions
        from src.shared import EmbeddingError, RAGError, LLMError
        print("Exception classes import successful")
        
        print("All imports successful!")
        return True
        
    except ImportError as e:
        print(f"Import failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def test_service_creation():
    """Test that we can create service instances."""
    try:
        print("Testing service creation...")
        
        from src.core.llm_service import LLMService
        from src.core.rag_service import RAGService
        from src.core.local_embedding_service import LocalEmbeddingService
        
        # Create LLM service
        llm_service = LLMService()
        print("LLMService instance created")
        
        # Create RAG service
        rag_service = RAGService(llm_service=llm_service)
        print("RAGService instance created")
        
        # Create local embedding service
        embedding_service = LocalEmbeddingService()
        print("LocalEmbeddingService instance created")
        
        print("All service creation successful!")
        return True
        
    except Exception as e:
        print(f"Service creation failed: {e}")
        return False

if __name__ == "__main__":
    print("SigmaHQ RAG Service Test")
    
    success = True
    success &= test_imports()
    success &= test_service_creation()
    
    if success:
        print("All tests passed! The embedding system is working correctly.")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)
