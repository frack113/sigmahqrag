#!/usr/bin/env python3
"""Test LLM download endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_download(repo_id="meta-llama/Llama-3.2-1B-Instruct-GGUF", filename=None):
    """Test POST /llm/download."""
    print(f"WARNING: This will download a model from HuggingFace!")
    confirm = input("Continue? (y/n): ")
    if confirm.lower() != "y":
        print("Cancelled")
        return
    
    response = requests.post(
        f"{BASE_URL}/llm/download",
        json={"repo_id": repo_id, "filename": filename, "expected_hash": None}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Success: {data.get('success')}")
        print(f"Path: {data.get('path')}")
    else:
        print(f"Error: {data}")

if __name__ == "__main__":
    test_download()