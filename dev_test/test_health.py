#!/usr/bin/env python3
"""Test health endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_health():
    """Test the /health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_health()