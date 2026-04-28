#!/usr/bin/env python3
"""Test Admin Backend API endpoints."""

import argparse
import json

import requests

BASE_URL = "http://localhost:7860"


def cmd_download(url: str, service: str, version: str) -> None:
    """Start a binary download."""
    params = {"action": "download", "service": service, "version": version}
    response = requests.post(f"{url}/admin/backend/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def cmd_cancel(url: str, download_id: str) -> None:
    """Cancel a download."""
    params = {"action": "cancel", "download_id": download_id}
    response = requests.post(f"{url}/admin/backend/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def cmd_progress(url: str, download_id: str) -> None:
    """Get download progress via SSE stream."""
    params = {"action": "progress", "download_id": download_id}
    response = requests.get(f"{url}/admin/backend/", params=params, stream=True)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(json.dumps(response.json(), indent=2))
        return
    for line in response.iter_lines():
        if line:
            print(line.decode())


def cmd_apply(url: str, service: str, version: str) -> None:
    """Apply an update."""
    params = {"action": "apply", "service": service, "version": version}
    response = requests.post(f"{url}/admin/backend/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def cmd_rollback(url: str, service: str) -> None:
    """Rollback an update."""
    params = {"action": "rollback", "service": service}
    response = requests.post(f"{url}/admin/backend/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def cmd_status(url: str) -> None:
    """Get update status."""
    params = {"action": "status"}
    response = requests.get(f"{url}/admin/backend/", params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Admin Backend API endpoints")
    parser.add_argument("--url", default=BASE_URL, help="Base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_download = subparsers.add_parser("download", help="Start a binary download")
    p_download.add_argument("--service", default="llama", choices=["llama", "qdrant"])
    p_download.add_argument("--version", required=True, help="Version to download")

    p_cancel = subparsers.add_parser("cancel", help="Cancel a download")
    p_cancel.add_argument("--download-id", required=True, help="Download ID to cancel")

    p_progress = subparsers.add_parser("progress", help="Get download progress")
    p_progress.add_argument("--download-id", required=True, help="Download ID")

    p_apply = subparsers.add_parser("apply", help="Apply an update")
    p_apply.add_argument("--service", default="llama", choices=["llama", "qdrant"])
    p_apply.add_argument("--version", required=True, help="Version to apply")

    p_rollback = subparsers.add_parser("rollback", help="Rollback an update")
    p_rollback.add_argument("--service", default="llama", choices=["llama", "qdrant"])

    _ = subparsers.add_parser("status", help="Get update status")

    args = parser.parse_args()

    match args.command:
        case "download":
            cmd_download(args.url, args.service, args.version)
        case "cancel":
            cmd_cancel(args.url, args.download_id)
        case "progress":
            cmd_progress(args.url, args.download_id)
        case "apply":
            cmd_apply(args.url, args.service, args.version)
        case "rollback":
            cmd_rollback(args.url, args.service)
        case "status":
            cmd_status(args.url)


if __name__ == "__main__":
    main()
