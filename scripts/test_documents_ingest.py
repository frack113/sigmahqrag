#!/usr/bin/env python3
"""Test documents ingest endpoint."""
import os
import requests

BASE_URL = "http://localhost:7860"

def get_token():
    """Login and get token."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    return resp.json().get("access_token") if resp.status_code == 200 else None

def test_ingest(directory=None, recursive=True):
    """Test the /documents/ingest endpoint."""
    token = get_token()
    if not token:
        print("Login failed")
        return
    
    response = requests.post(
        f"{BASE_URL}/documents/ingest",
        json={"directory": directory, "recursive": recursive},
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total: {data.get('total_files')}")
    print(f"Success: {data.get('successful')}")
    print(f"Failed: {data.get('failed')}")

if __name__ == "__main__":
    test_ingest()