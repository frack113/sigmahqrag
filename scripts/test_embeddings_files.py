#!/usr/bin/env python3
"""Test embeddings files endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_files(repo_id="sentence-transformers/all-MiniLM-L6-v2"):
    """Test GET /embeddings/{repo_id}/files."""
    response = requests.get(f"{BASE_URL}/embeddings/{repo_id}/files")
    print(f"Status: {response.status_code}")
    data = response.json()
    files = data.get("files", [])
    print(f"Files: {len(files)}")
    for f in files[:5]:
        print(f"  - {f}")

if __name__ == "__main__":
    test_files()