"""Llama.cpp package."""

from pathlib import Path

from src.config.settings import get_config

from .client import LlamaClient
from .health import check_health
from .service import LlamaBinaryService

LlamaService = LlamaBinaryService


def _detect_llama_server_binary() -> Path | None:
    """Find the llama-server executable in the expected location."""
    import sys

    config = get_config()
    bin_dir = config.resolve_llamacpp_bin_path()

    if sys.platform == "win32":
        candidates = ("llama-server.exe", "llama-server")
    else:
        candidates = ("llama-server", "llama-server.exe")

    for name in candidates:
        candidate = bin_dir / name
        if candidate.is_file():
            return candidate
    return None


def _try_get_llama_version_from_binary() -> str | None:
    """Try to detect llama.cpp version by running the binary with --version."""
    import re
    import subprocess

    binary = _detect_llama_server_binary()
    if not binary:
        return None

    try:
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        output = result.stdout + result.stderr

        patterns = [
            r"\b(b\d+)\b",
            r"version[:\s]+(b\d+)",
            r"llama.cpp\s+(b\d+)",
            r"build\s+(b\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

        num_match = re.search(r"\b(\d{4,})\b", output)
        if num_match:
            return f"b{num_match.group(1)}"

        return None
    except Exception:
        return None


def get_version() -> str | None:
    """Get current llama.cpp version.

    Detects from config first, then falls back to binary detection if version is "0".
    """
    config = get_config()
    version = config.llamacpp_version

    if version != "0":
        return version

    binary = _detect_llama_server_binary()
    if binary:
        detected = _try_get_llama_version_from_binary()
        if detected:
            config.llamacpp_version = detected
            config.save()
            return detected
        return "installed"

    return version


def set_version(version: str) -> None:
    """Set llama.cpp version."""
    config = get_config()
    config.llamacpp_version = version
    config.save()


__all__ = [
    "LlamaClient",
    "LlamaBinaryService",
    "LlamaService",
    "check_health",
    "get_version",
    "set_version",
]
