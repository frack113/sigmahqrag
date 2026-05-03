#!/usr/bin/env python3
"""Test GitHub Admin API endpoints."""

import argparse

import requests

BASE_URL = "http://localhost:7860"


def cmd_list(url: str) -> None:
    """List all GitHub repositories."""
    response = requests.get(f"{url}/admin/github/", params={"action": "list"})
    print(f"Status: {response.status_code}")
    data = response.json()
    repos = data.get("repos", [])
    print(f"Repositories: {len(repos)}")
    for repo in repos:
        print(f"  - {repo.get('org')}/{repo.get('name')} at {repo.get('path')}")
        metadata = repo.get("metadata")
        if metadata:
            print(f"    Org: {metadata.get('org')}, Branch: {metadata.get('branch')}")
            print(f"    Extensions: {metadata.get('extensions_to_index')}")


def cmd_info(url: str, org: str, name: str) -> None:
    """Get repository info."""
    response = requests.get(
        f"{url}/admin/github/", params={"action": "info", "org": org, "name": name}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Org: {data.get('org')}")
        print(f"Name: {data.get('name')}")
        print(f"Path: {data.get('path')}")
        metadata = data.get("metadata")
        if metadata:
            print(f"Branch: {metadata.get('branch', 'N/A')}")
            print(f"Extensions to index: {metadata.get('extensions_to_index', [])}")
        else:
            print("No metadata found")
    else:
        print(f"Error: {data}")


def cmd_clone(url: str, org: str, name: str, branch: str = "main") -> None:
    """Clone a GitHub repository."""
    params = {
        "action": "clone",
        "org": org,
        "name": name,
        "branch": branch,
    }

    response = requests.post(f"{url}/admin/github/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def cmd_update(url: str, org: str, name: str, branch: str | None = None) -> None:
    """Update a GitHub repository."""
    params = {"action": "update", "org": org, "name": name}
    if branch:
        params["branch"] = branch

    response = requests.post(f"{url}/admin/github/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def cmd_update_metadata(url: str, org: str, name: str) -> None:
    """Update repository metadata (extensions, branch)."""
    import sys
    from typing import Any

    params: dict[str, Any] = {"action": "update-metadata", "org": org, "name": name}

    # Parse additional arguments
    if "--branch" in sys.argv:
        idx = sys.argv.index("--branch")
        if idx + 1 < len(sys.argv):
            params["branch"] = sys.argv[idx + 1]

    if "--extensions" in sys.argv:
        idx = sys.argv.index("--extensions")
        if idx + 1 < len(sys.argv):
            params["extensions_to_index"] = sys.argv[idx + 1].split(",")

    response = requests.post(f"{url}/admin/github/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def cmd_delete(url: str, org: str, name: str, force: bool) -> None:
    """Delete a GitHub repository."""
    if not force:
        msg = f"WARNING: This will delete repository {org}/{name}!"
        confirm = input(f"{msg}\nContinue? (y/n): ")
        if confirm.lower() != "y":
            print("Cancelled")
            return

    params = {"action": "delete", "org": org, "name": name}

    response = requests.post(f"{url}/admin/github/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test GitHub Admin API endpoints")
    parser.add_argument("--url", default=BASE_URL, help="Base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list", help="List all repositories")
    _ = p_list

    p_info = subparsers.add_parser("info", help="Get repository info")
    p_info.add_argument("org", help="Organization name")
    p_info.add_argument("name", help="Repository name")

    p_clone = subparsers.add_parser("clone", help="Clone a repository")
    p_clone.add_argument("--org", required=True, help="GitHub organization")
    p_clone.add_argument("--name", required=True, help="Repository name")
    p_clone.add_argument("--branch", default="main", help="Branch to clone (required)")

    p_update = subparsers.add_parser("update", help="Update a repository")
    p_update.add_argument("org", help="Organization name")
    p_update.add_argument("name", help="Repository name")
    p_update.add_argument("--branch", help="Branch to update")

    p_update_meta = subparsers.add_parser(
        "update-metadata", help="Update repository metadata"
    )
    p_update_meta.add_argument("org", help="Organization name")
    p_update_meta.add_argument("name", help="Repository name")
    p_update_meta.add_argument("--branch", help="Branch to track")
    p_update_meta.add_argument(
        "--extensions", help="Comma-separated list of extensions (e.g., *.yml,*.yaml)"
    )

    p_delete = subparsers.add_parser("delete", help="Delete a repository")
    p_delete.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation"
    )
    p_delete.add_argument("org", help="Organization name")
    p_delete.add_argument("name", help="Repository name")

    args = parser.parse_args()

    match args.command:
        case "list":
            cmd_list(args.url)
        case "info":
            cmd_info(args.url, args.org, args.name)
        case "clone":
            cmd_clone(args.url, args.org, args.name, args.branch)
        case "update":
            cmd_update(args.url, args.org, args.name, args.branch)
        case "update-metadata":
            cmd_update_metadata(args.url, args.org, args.name)
        case "delete":
            cmd_delete(args.url, args.org, args.name, args.force)


if __name__ == "__main__":
    main()
