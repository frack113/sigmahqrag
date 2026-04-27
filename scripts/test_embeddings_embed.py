#!/usr/bin/env python3
"""Test embeddings embed endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_embed(texts=None):
    """Test POST /embeddings/embed."""
    if texts is None:
        texts = ["Hello world", "Sigma rules are cool"]
    
    response = requests.post(
        f"{BASE_URL}/embeddings/embed",
        json={"text": texts, "model_name": None}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        embeddings = data.get("embeddings", [])
        print(f"Embeddings: {len(embeddings)}")
        if embeddings:
            print(f"Shape: {len(embeddings[0])}")
    else:
        print(f"Error: {data}")

if __name__ == "__main__":
    test_embed()