"""Embedder."""



class Embedder:
    """Document embedder."""

    def __init__(self, model_name: str = "nomic-embed-text") -> None:
        """Initialize the embedder."""
        self.model_name = model_name

    def embed(self, text: str) -> list[float]:
        """Embed text."""
        return []
