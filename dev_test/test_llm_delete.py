#!/usr/bin/env python3
"""Test LLM delete endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def get_token():
    """Login and get token."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    return resp.json().get("access_token") if resp.status_code == 200 else None

def test_delete(repo_id):
    """Test DELETE /llm/{repo_id}."""
    token = get_token()
    if not token:
        print("Login failed")
        return
    
    response = requests.delete(
        f"{BASE_URL}/llm/{repo_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")

if __name__ == "__main__":
    test_delete("meta-llama/Llama-3.2-1B-Instruct-GGUF")