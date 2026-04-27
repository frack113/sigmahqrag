#!/usr/bin/env python3
"""Test LLM list files endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_list_files(repo_id="meta-llama/Llama-3.2-1B-Instruct-GGUF"):
    """Test GET /llm/list-files/{repo_id}."""
    response = requests.get(f"{BASE_URL}/llm/list-files/{repo_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        files = data.get("files", [])
        print(f"Files: {len(files)}")
        for f in files[:5]:
            print(f"  - {f.get('filename')}")
    else:
        print(f"Error: {data}")

if __name__ == "__main__":
    test_list_files()