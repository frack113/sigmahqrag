#!/usr/bin/env python3
"""Test auth login endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_login(username="admin", password="admin"):
    """Test the /auth/login endpoint."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Token: {data.get('access_token', '')[:50]}...")
        return data.get("access_token")
    else:
        print(f"Error: {data}")
        return None

if __name__ == "__main__":
    test_login()