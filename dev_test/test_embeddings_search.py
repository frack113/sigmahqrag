#!/usr/bin/env python3
"""Test embeddings search endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_search(query="sentence-transformers", limit=10):
    """Test GET /embeddings/search."""
    response = requests.get(
        f"{BASE_URL}/embeddings/search",
        params={"query": query, "limit": limit}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    models = data.get("models", [])
    print(f"Results: {len(models)}")

if __name__ == "__main__":
    test_search()