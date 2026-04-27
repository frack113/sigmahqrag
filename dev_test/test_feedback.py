#!/usr/bin/env python3
"""Test feedback submit and get stats."""
import requests

BASE_URL = "http://localhost:7860"

def get_token():
    """Login and get token."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    return resp.json().get("access_token") if resp.status_code == 200 else None

def test_submit():
    """Test POST /feedback."""
    response = requests.post(
        f"{BASE_URL}/feedback",
        json={"query": "test query", "helpful": True}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Feedback ID: {data.get('feedback_id')}")

def test_stats():
    """Test GET /feedback/stats."""
    token = get_token()
    if not token:
        print("Login failed")
        return
    
    response = requests.get(
        f"{BASE_URL}/feedback/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Stats: {data}")

if __name__ == "__main__":
    test_submit()
    test_stats()