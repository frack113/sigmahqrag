#!/usr/bin/env python3
"""Test LLM installed endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_installed():
    """Test GET /llm/installed."""
    response = requests.get(f"{BASE_URL}/llm/installed")
    print(f"Status: {response.status_code}")
    data = response.json()
    models = data.get("models", [])
    print(f"Installed: {len(models)}")
    for m in models:
        print(f"  - {m.get('repo_id')}")

if __name__ == "__main__":
    test_installed()