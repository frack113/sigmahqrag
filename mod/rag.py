# RAG (Retrieval-Augmented Generation) Module
import logging
from sentence_transformers import SentenceTransformer


class RAGSystem:
    """
    A system for generating embeddings locally using SentenceTransformer.
    
    Methods:
        - generate_embeddings: Generate embeddings for the given text.
    """

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)
        self.model = SentenceTransformer(model_name)

    def generate_embeddings(self, text: str) -> list:
        """
        Generate embeddings for the given text.
        
        Args:
            text (str): The input text to generate embeddings for.
            
        Returns:
            list: The generated embeddings.
        """
        return self.model.encode(text)