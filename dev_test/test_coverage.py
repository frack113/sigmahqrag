#!/usr/bin/env python3
"""Test coverage check endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_coverage():
    """Test GET /check-coverage."""
    response = requests.get(f"{BASE_URL}/check-coverage")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_coverage()