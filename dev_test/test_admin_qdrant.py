#!/usr/bin/env python3
"""Test admin qdrant start/stop endpoints."""
import requests

BASE_URL = "http://localhost:7860"

def get_token():
    """Login and get token."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    return resp.json().get("access_token") if resp.status_code == 200 else None

def test_qdrant_start():
    """Test POST /admin/qdrant/start."""
    token = get_token()
    if not token:
        print("Login failed")
        return
    
    response = requests.post(
        f"{BASE_URL}/admin/qdrant/start",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_qdrant_stop():
    """Test POST /admin/qdrant/stop."""
    token = get_token()
    if not token:
        print("Login failed")
        return
    
    response = requests.post(
        f"{BASE_URL}/admin/qdrant/stop",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        test_qdrant_stop()
    else:
        test_qdrant_start()