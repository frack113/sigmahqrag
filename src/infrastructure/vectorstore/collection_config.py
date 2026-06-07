"""Per-collection configuration for Qdrant vector stores.

Each collection has its own vector size and distance metric. These values
must match the embedding model's output dimension and the distance function
used when creating the collection.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client.http.models import Distance


@dataclass
class CollectionConfig:
    """Configuration for a Qdrant collection.

    Attributes:
        vector_size: Number of dimensions in the embedding vectors.
            Must match the output dimension of the embedding model.
        distance: Distance metric for similarity search.
    """

    vector_size: int = 384
    distance: Distance = Distance.COSINE
