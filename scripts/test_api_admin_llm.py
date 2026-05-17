#!/usr/bin/env python3
"""Test LLM API endpoints."""

import argparse

import requests

BASE_URL = "http://localhost:7860"


def cmd_list(url: str, repo_id: str) -> None:
    """List GGUF files for a model."""
    response = requests.get(f"{url}/admin/llm/?action=list&repo_id={repo_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        files = data.get("files", [])
        print(f"Files: {len(files)}")
        for f in files[:10]:
            size = f.get("size") or 0
            size_mb = size / 1024 / 1024
            print(f"  - {f.get('filename')} ({size_mb:.1f}MB)")
    else:
        print(f"Error: {data}")


def cmd_installed(url: str) -> None:
    """List installed models."""
    response = requests.get(f"{url}/admin/llm/?action=installed")
    print(f"Status: {response.status_code}")
    data = response.json()
    models = data.get("models", [])
    print(f"Installed: {len(models)}")
    for m in models:
        print(f"  Repo: {m.get('repo_id')} [{m.get('status')}]")
        for f in m.get("files", []):
            size_mb = f.get("size", 0) / 1024 / 1024
            print(f"    - {f.get('filename')} ({size_mb:.1f}MB)")


def cmd_info(url: str, repo_id: str) -> None:
    """Get model info."""
    response = requests.get(f"{url}/admin/llm/?action=info&repo_id={repo_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Repo: {data.get('id')}")
        print(f"Author: {data.get('author')}")
        print(f"Modified: {data.get('last_modified')}")
        siblings = data.get("siblings", [])
        print(f"GGUF files: {len(siblings)}")
        for f in siblings:
            size = f.get("size") or 0
            size_mb = size / 1024 / 1024
            print(f"  - {f.get('filename')} ({size_mb:.1f}MB)")
    else:
        print(f"Error: {data}")


def cmd_download(url: str, repo_id: str, filename: str | None, force: bool) -> None:
    """Download a model."""
    if not force:
        print("WARNING: This will download a model from HuggingFace!")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

    params = {"action": "download", "repo_id": repo_id}
    if filename:
        params["filename"] = filename

    response = requests.post(f"{url}/admin/llm/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Success: {data.get('success')}")
        print(f"Path: {data.get('path')}")
        print(f"Size: {data.get('size') / 1024 / 1024:.1f}MB")
    else:
        print(f"Error: {data}")


def cmd_delete(url: str, repo_id: str, filename: str | None, force: bool) -> None:
    """Delete a model."""
    if not force:
        msg = f"WARNING: This will delete model {repo_id}!"
        if filename:
            msg = f"WARNING: This will delete {filename} from {repo_id}!"
        confirm = input(f"{msg}\nContinue? (y/n): ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

    params = {"action": "delete", "repo_id": repo_id}
    if filename:
        params["filename"] = filename

    response = requests.post(f"{url}/admin/llm/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test LLM API endpoints")
    parser.add_argument("--url", default=BASE_URL, help="Base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list", help="List GGUF files")
    p_list.add_argument("repo_id", nargs="?", default="meta-llama/Llama-3.2-1B-Instruct-GGUF")

    p_installed = subparsers.add_parser("installed", help="List installed models")
    _ = p_installed

    p_info = subparsers.add_parser("info", help="Get model info")
    p_info.add_argument("repo_id", nargs="?", default="meta-llama/Llama-3.2-1B-Instruct-GGUF")

    p_download = subparsers.add_parser("download", help="Download a model")
    p_download.add_argument("--filename", "-n", help="Specific filename")
    p_download.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    p_download.add_argument("repo_id", nargs="?", default="meta-llama/Llama-3.2-1B-Instruct-GGUF")
    p_download.add_argument(
        "filename", nargs="?", help="Specific filename (alternative to --filename)"
    )

    p_delete = subparsers.add_parser("delete", help="Delete a model")
    p_delete.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    p_delete.add_argument("repo_id", nargs="?", default="meta-llama/Llama-3.2-1B-Instruct-GGUF")
    p_delete.add_argument("filename", nargs="?", help="Specific filename to delete")

    args = parser.parse_args()

    match args.command:
        case "list":
            cmd_list(args.url, args.repo_id)
        case "installed":
            cmd_installed(args.url)
        case "info":
            cmd_info(args.url, args.repo_id)
        case "download":
            fn = args.filename or getattr(args, "filename", None)
            cmd_download(args.url, args.repo_id, fn, args.force)
        case "delete":
            fn = args.filename or getattr(args, "filename", None)
            cmd_delete(args.url, args.repo_id, fn, args.force)


if __name__ == "__main__":
    main()
