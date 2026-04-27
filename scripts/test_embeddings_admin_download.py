#!/usr/bin/env python3
"""Test embeddings admin download endpoint."""
import requests

BASE_URL = "http://localhost:7860"


def get_token():
    """Login and get token."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "admin"}
    )
    return resp.json().get("access_token") if resp.status_code == 200 else None


def test_admin_download(repo_id="sentence-transformers/all-MiniLM-L6-v2", filename=None):
    """Test POST /admin/embeddings/?action=download&repo_id=..."""
    token = get_token()
    if not token:
        print("Login failed")
        return

    print("WARNING: This will download an embedding model!")
    confirm = input("Continue? (y/n): ")
    if confirm.lower() != "y":
        print("Cancelled")
        return

    params = {"action": "download", "repo_id": repo_id}
    if filename:
        params["filename"] = filename

    response = requests.post(
        f"{BASE_URL}/admin/embeddings/",
        params=params,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


if __name__ == "__main__":
    test_admin_download()
