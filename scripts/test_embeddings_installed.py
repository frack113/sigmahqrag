#!/usr/bin/env python3
"""Test embeddings installed endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_installed():
    """Test GET /embeddings/installed."""
    response = requests.get(f"{BASE_URL}/embeddings/installed")
    print(f"Status: {response.status_code}")
    data = response.json()
    models = data.get("models", {})
    print(f"Installed: {len(models)}")

if __name__ == "__main__":
    test_installed()