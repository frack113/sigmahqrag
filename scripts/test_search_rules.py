#!/usr/bin/env python3
"""Test search rules endpoint."""
import requests

BASE_URL = "http://localhost:7860"

def test_search_rules(query="powershell", limit=10):
    """Test the /api/search-rules endpoint."""
    response = requests.post(
        f"{BASE_URL}/api/search-rules",
        json={"query": query, "limit": limit}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Count: {data.get('meta', {}).get('count', 0)}")
    if data.get("data"):
        for item in data["data"][:3]:
            print(f"  - {item.get('title', 'N/A')}")

if __name__ == "__main__":
    test_search_rules()