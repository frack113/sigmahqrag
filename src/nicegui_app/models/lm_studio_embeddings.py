"""
Custom LM Studio Embeddings wrapper for LangChain compatibility.

This module provides a custom embedding class that works correctly with LM Studio's
embedding API, bypassing LangChain's request formatting issues.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class LMStudioEmbeddings(Embeddings):
    """
    Custom embedding class for LM Studio compatibility.

    This class bypasses LangChain's request formatting issues by directly
    calling LM Studio's embedding API with the correct format.
    """

    def __init__(
        self,
        model: str = "text-embedding-all-minilm-l6-v2-embedding",
        base_url: str = "http://localhost:1234",
        api_key: str = "lm-studio",
    ):
        """
        Initialize the LM Studio embeddings.

        Args:
            model: Name of the embedding model to use
            base_url: Base URL for LM Studio server
            api_key: API key for LM Studio
        """
        self.model = model
        self.base_url = f"{base_url}/v1"
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If the API call fails
        """
        if not texts:
            return []

        try:
            # LM Studio expects the input as a string or array of strings
            # We'll send it as an array of strings for consistency
            payload = {"model": self.model, "input": texts}

            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            # Extract embeddings from the response
            embeddings = []
            for item in data.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
                else:
                    logger.warning("No embedding found in response item")
                    embeddings.append([])

            logger.info(f"Generated embeddings for {len(texts)} documents")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating document embeddings: {e}")
            raise RuntimeError(f"Failed to generate document embeddings: {str(e)}")

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector

        Raises:
            RuntimeError: If the API call fails
        """
        try:
            # For single text, send as string (not array)
            payload = {"model": self.model, "input": text}

            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self.headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            # Extract embedding from the response
            if data.get("data") and len(data["data"]) > 0:
                embedding = data["data"][0].get("embedding", [])
                logger.info("Generated embedding for query")
                return embedding
            else:
                logger.warning("No embedding found in response")
                return []

        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise RuntimeError(f"Failed to generate query embedding: {str(e)}")
