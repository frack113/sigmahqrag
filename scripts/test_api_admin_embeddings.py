#!/usr/bin/env python3
"""Test Embeddings Admin API endpoints."""

import argparse

import requests

BASE_URL = "http://localhost:7860"


def cmd_installed(url: str) -> None:
    """List installed embedding models."""
    response = requests.get(f"{url}/admin/embeddings/?action=installed")
    print(f"Status: {response.status_code}")
    data = response.json()
    models = data.get("models", {})
    print(f"Installed: {len(models)}")
    for repo_id, info in models.items():
        size_mb = info.get("file_size", 0) / 1024 / 1024
        dim = info.get("dimension", "N/A")
        print(f"  - {repo_id} ({size_mb:.1f}MB) dim={dim}")


def cmd_info(url: str, repo_id: str) -> None:
    """Get embedding model info."""
    response = requests.get(f"{url}/admin/embeddings/?action=info&repo_id={repo_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        info = data.get("model", {})
        print(f"Repo: {repo_id}")
        print(f"Path: {info.get('local_path')}")
        print(f"Size: {info.get('file_size', 0) / 1024 / 1024:.1f}MB")
        print(f"Dimension: {info.get('dimension')}")
        print(f"Status: {info.get('status')}")
    else:
        print(f"Error: {data}")


def cmd_download(url: str, repo_id: str, force: bool) -> None:
    """Download an embedding model."""
    if not force:
        print("WARNING: This will download a model from HuggingFace!")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

    params = {"action": "download", "repo_id": repo_id}

    response = requests.post(f"{url}/admin/embeddings/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Success: {data.get('success')}")
        print(f"Path: {data.get('path')}")
    else:
        print(f"Error: {data}")


def cmd_delete(url: str, repo_id: str, force: bool) -> None:
    """Delete an embedding model."""
    if not force:
        msg = f"WARNING: This will delete model {repo_id}!"
        confirm = input(f"{msg}\nContinue? (y/n): ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

    params = {"action": "delete", "repo_id": repo_id}

    response = requests.post(f"{url}/admin/embeddings/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Embeddings Admin API endpoints")
    parser.add_argument("--url", default=BASE_URL, help="Base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_installed = subparsers.add_parser("installed", help="List installed models")
    _ = p_installed

    p_info = subparsers.add_parser("info", help="Get model info")
    p_info.add_argument("repo_id", nargs="?", default="sentence-transformers/all-MiniLM-L6-v2")

    p_download = subparsers.add_parser("download", help="Download a model")
    p_download.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    p_download.add_argument("repo_id", nargs="?", default="sentence-transformers/all-MiniLM-L6-v2")

    p_delete = subparsers.add_parser("delete", help="Delete a model")
    p_delete.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    p_delete.add_argument("repo_id", nargs="?", default="sentence-transformers/all-MiniLM-L6-v2")

    args = parser.parse_args()

    match args.command:
        case "installed":
            cmd_installed(args.url)
        case "info":
            cmd_info(args.url, args.repo_id)
        case "download":
            cmd_download(args.url, args.repo_id, args.force)
        case "delete":
            cmd_delete(args.url, args.repo_id, args.force)


if __name__ == "__main__":
    main()
