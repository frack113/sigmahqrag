"""Golden set data model and I/O for search quality evaluation.

A golden set is a curated collection of ``(query, relevant_doc_ids)`` pairs
used to measure retrieval quality (recall@k, precision@k, MRR).

File format (JSON)::

    {
      "metadata": {
        "version": 1,
        "description": "Sigma rules retrieval — 50 queries",
        "created_at": "2025-01-15T10:30:00Z"
      },
      "queries": [
        {
          "id": "q001",
          "query": "detect powershell execution",
          "collection": "sigma_rules",
          "relevant_doc_ids": ["rule-abc-123", "rule-def-456"],
          "k": 10
        }
      ]
    }
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class GoldenQuery:
    """A single golden-set query with its ground-truth relevant documents."""

    id: str
    query: str
    collection: str
    relevant_doc_ids: list[str]
    k: int = 10

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoldenQuery":
        return cls(
            id=data["id"],
            query=data["query"],
            collection=data["collection"],
            relevant_doc_ids=data["relevant_doc_ids"],
            k=data.get("k", 10),
        )


@dataclass
class GoldenSet:
    """A complete golden set with metadata and queries."""

    description: str = ""
    queries: list[GoldenQuery] = field(default_factory=list)

    def add(
        self,
        query: str,
        collection: str,
        relevant_doc_ids: list[str],
        k: int = 10,
        query_id: str | None = None,
    ) -> GoldenQuery:
        q = GoldenQuery(
            id=query_id or _make_id(len(self.queries)),
            query=query,
            collection=collection,
            relevant_doc_ids=relevant_doc_ids,
            k=k,
        )
        self.queries.append(q)
        return q

    def __len__(self) -> int:
        return len(self.queries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "version": 1,
                "description": self.description,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "num_queries": len(self.queries),
            },
            "queries": [q.to_dict() for q in self.queries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoldenSet":
        queries = [GoldenQuery.from_dict(q) for q in data.get("queries", [])]
        return cls(
            description=data.get("metadata", {}).get("description", ""),
            queries=queries,
        )


def _make_id(index: int) -> str:
    return f"q{index:04d}"


def load_golden_set(path: str | Path) -> GoldenSet:
    """Load a golden set from a JSON file.

    Args:
        path: Path to the golden set JSON file.

    Returns:
        Parsed GoldenSet.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON structure is invalid.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "queries" not in data:
        raise ValueError(f"Golden set file missing 'queries' key: {path}")
    return GoldenSet.from_dict(data)


def save_golden_set(golden_set: GoldenSet, path: str | Path) -> Path:
    """Save a golden set to a JSON file.

    Args:
        golden_set: The golden set to save.
        path: Output file path.

    Returns:
        The resolved output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(golden_set.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def create_sample_golden_set() -> GoldenSet:
    """Create a small sample golden set for development / testing.

    These queries use doc_ids that correspond to typical Sigma rule IDs
    found in the sigma_rules collection.  Replace with real ground truth
    data for production evaluation.
    """
    gs = GoldenSet(description="Sample golden set for development")
    gs.add(
        query="detect powershell execution",
        collection="sigma_rules",
        relevant_doc_ids=["sample-rule-001", "sample-rule-002"],
        k=10,
    )
    gs.add(
        query="CMD.exe suspicious command line",
        collection="sigma_rules",
        relevant_doc_ids=["sample-rule-003"],
        k=10,
    )
    gs.add(
        query="network connection to C2 server",
        collection="sigma_docs",
        relevant_doc_ids=["sample-doc-001"],
        k=10,
    )
    gs.add(
        query="Sigma rule format specification",
        collection="sigma_spec",
        relevant_doc_ids=["sample-spec-001"],
        k=10,
    )
    return gs
