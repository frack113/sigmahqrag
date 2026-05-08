#!/usr/bin/env python3
"""Test Admin Backend API v1 endpoints."""

import argparse
import json

import requests

BASE_URL = "http://localhost:7860"


def cmd_download(url: str, service: str, version: str) -> None:
    """Start a binary download."""
    endpoint = f"{url}/api/v1/{service}/download"
    params = {"version": version}
    response = requests.post(endpoint, params=params)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    if data.get("status") == "skipped":
        print("Note: Version already installed, download skipped")


def cmd_cancel(url: str, service: str, download_id: str) -> None:
    """Cancel a download."""
    endpoint = f"{url}/api/v1/{service}/cancel/{download_id}"
    response = requests.post(endpoint)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def cmd_progress(url: str, service: str, download_id: str) -> None:
    """Get download progress via SSE stream."""
    endpoint = f"{url}/api/v1/{service}/progress/{download_id}"
    response = requests.get(endpoint, stream=True)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(json.dumps(response.json(), indent=2))
        return
    for line in response.iter_lines():
        if line:
            print(line.decode())


def cmd_status(url: str, service: str) -> None:
    """Get service status."""
    endpoint = f"{url}/api/v1/{service}/status"
    response = requests.get(endpoint)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Admin Backend API v1 endpoints")
    parser.add_argument("--url", default=BASE_URL, help="Base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_download = subparsers.add_parser("download", help="Start a binary download")
    p_download.add_argument("--service", default="llama", choices=["llama", "qdrant"])
    p_download.add_argument(
        "--version", default="latest", help="Version to download (default: latest)"
    )

    p_cancel = subparsers.add_parser("cancel", help="Cancel a download")
    p_cancel.add_argument("--service", default="llama", choices=["llama", "qdrant"])
    p_cancel.add_argument("--download-id", required=True, help="Download ID to cancel")

    p_progress = subparsers.add_parser("progress", help="Get download progress")
    p_progress.add_argument("--service", default="llama", choices=["llama", "qdrant"])
    p_progress.add_argument("--download-id", required=True, help="Download ID")

    p_status = subparsers.add_parser("status", help="Get service status")
    p_status.add_argument(
        "--service", default="llama", choices=["llama", "qdrant"], required=True
    )

    args = parser.parse_args()

    match args.command:
        case "download":
            cmd_download(args.url, args.service, args.version)
        case "cancel":
            cmd_cancel(args.url, args.service, args.download_id)
        case "progress":
            cmd_progress(args.url, args.service, args.download_id)
        case "status":
            cmd_status(args.url, args.service)


if __name__ == "__main__":
    main()
