#!/usr/bin/env python3
"""Test Admin Services API endpoints."""

import argparse

import requests

BASE_URL = "http://localhost:7860"


def cmd_start(url: str, service: str, model_path: str | None) -> None:
    """Start a service."""
    if service == "qdrant":
        endpoint = f"{url}/api/v1/qdrant"
        payload = {"action": "service_control", "payload": {"command": "start"}}
        response = requests.post(endpoint, json=payload)
    else:
        params = {"action": "start", "service": service}
        data = {}
        if model_path:
            data["model_path"] = model_path
        response = requests.post(
            f"{url}/admin/services/",
            params=params,
            json=data if data else None,
        )
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Success: {data.get('success') or data.get('message')}")
        if data.get("pid"):
            print(f"PID: {data.get('pid')}")
    else:
        print(f"Error: {data}")


def cmd_stop(url: str, service: str) -> None:
    """Stop a service."""
    if service == "qdrant":
        endpoint = f"{url}/api/v1/qdrant"
        payload = {"action": "service_control", "payload": {"command": "stop"}}
        response = requests.post(endpoint, json=payload)
    else:
        params = {
            "action": "stop",
            "s_service": service,
        }  # Wait, I'll check the original
        # The original was: params = {"action": "stop", "service": service}
        params = {"action": "stop", "service": service}
        response = requests.post(
            f"{url}/admin/services/",
            params=params,
        )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")


def cmd_logs(url: str, service: str) -> None:
    """Get service logs."""
    params = {"action": "logs", "service": service}

    response = requests.get(
        f"{url}/admin/services/",
        params=params,
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if response.status_code == 200:
        print(f"Service: {data.get('service')}")
        print(f"Log file: {data.get('log_file')}")
        print(f"Logs:\n{data.get('logs')}")
    else:
        print(f"Error: {data}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Admin Services API endpoints")
    parser.add_argument("--url", default=BASE_URL, help="Base URL")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_start = subparsers.add_parser("start", help="Start a service")
    p_start.add_argument(
        "--service",
        default="llama",
        choices=["llama", "qdrant"],
        help="Service to start",
    )
    p_start.add_argument("--model-path", help="Model path for llama")

    p_stop = subparsers.add_parser("stop", help="Stop a service")
    p_stop.add_argument(
        "--service",
        default="llama",
        choices=["llama", "qdrant"],
        help="Service to stop",
    )

    p_logs = subparsers.add_parser("logs", help="Get service logs")
    p_logs.add_argument(
        "--service",
        default="llama",
        choices=["llama", "qdrant"],
        help="Service to get logs for",
    )

    args = parser.parse_args()

    match args.command:
        case "start":
            cmd_start(args.url, args.service, getattr(args, "model_path", None))
        case "stop":
            cmd_stop(args.url, args.service)
        case "logs":
            cmd_logs(args.url, args.service)


if __name__ == "__main__":
    main()
