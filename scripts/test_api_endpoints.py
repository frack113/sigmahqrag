#!/usr/bin/env python3
"""Test main API endpoints."""

import requests

BASE_URL = "http://localhost:7860"


def main():
    print("Testing API endpoints...")
    
    endpoints = [
        ("/health", "GET"),
        ("/chat", "GET"),
        ("/admin", "GET"),
        ("/admin/health", "GET"),
    ]
    
    for path, method in endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{path}")
            print(f"{method} {path}: {r.status_code}")
        except Exception as e:
            print(f"{method} {path}: ERROR - {e}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()