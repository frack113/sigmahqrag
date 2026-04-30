"""FastAPI dependencies."""

from functools import lru_cache

from src.core.services.embedding import EmbeddingManager
from src.core.services.manager import ModelManager
from src.git.repo_manager import RepositoryManager


@lru_cache
def get_embedding_manager() -> EmbeddingManager:
    """Get a singleton instance of the embedding manager."""
    return EmbeddingManager()


@lru_cache
def get_model_manager() -> ModelManager:
    """Get a singleton instance of the model manager."""
    return ModelManager()


@lru_cache
def get_github_repo_manager() -> RepositoryManager:
    """Get a singleton instance of the GitHub repository manager."""
    return RepositoryManager(repos_dir="data/github")
