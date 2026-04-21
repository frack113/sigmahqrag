"""Qdrant server service client."""

import logging
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class QdrantService:
    """Manage Qdrant server subprocess."""

    def __init__(
        self,
        binary_path: Path | str | None = None,
        port: int = 6333,
        host: str = "127.0.0.1",
        storage_path: Path | None = None,
    ) -> None:
        """Initialize QdrantService.

        Args:
            binary_path: Path to qdrant binary
            port: HTTP server port
            host: HTTP server host
            storage_path: Path for vector storage (default: "qdrant/storage")
        """
        if binary_path is None:
            from .download import get_binary_path

            binary_path = get_binary_path()

        self.binary_path = Path(binary_path)
        self.port = port
        self.host = host
        self.storage_path = storage_path or Path("qdrant/storage")
        self._process: subprocess.Popen[Any] | None = None

        if not self.binary_path.exists():
            logger.warning(
                f"Qdrant binary not found at {self.binary_path}. "
                "Run download_qdrant() first."
            )

    def start(self) -> subprocess.Popen:
        """Start Qdrant server.

        Returns:
            Popen process object

        Raises:
            FileNotFoundError: If binary does not exist
            OSError: If port is already in use
        """
        if not self.binary_path.exists():
            raise FileNotFoundError(
                f"Qdrant binary not found at {self.binary_path}. "
                "Run download_qdrant() first."
            )

        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}. Must be 1-65535.")

        if self._process is not None and self._process.poll() is None:
            logger.warning("Qdrant server already running")
            return self._process

        if not self.storage_path.exists():
            try:
                self.storage_path.mkdir(parents=True)
            except OSError as e:
                raise OSError(f"Failed to create storage directory: {e}") from e

        cmd = [
            str(self.binary_path),
            "--host", self.host,
            "--port", str(self.port),
            "--storage", str(self.storage_path),
        ]

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self._wait_for_server(30)

        logger.info(f"Qdrant server started on {self.host}:{self.port}")
        return self._process

    def _wait_for_server(self, timeout: int = 30) -> None:
        """Wait for server to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.health_check():
                return
            time.sleep(0.5)

        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

        raise TimeoutError("Qdrant server failed to start within timeout")

    def health_check(self) -> bool:
        """Check if server is running and responsive.

        Returns:
            True if server is healthy
        """
        try:
            request = urllib.request.Request(
                f"http://{self.host}:{self.port}/readyz",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                return 200 <= response.status < 300
        except urllib.error.URLError as e:
            logger.debug(f"Health check failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Health check error: {type(e).__name__}: {e}")
            return False

    def stop(self) -> None:
        """Stop Qdrant server."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None
            logger.info("Qdrant server stopped")

    def version(self) -> str:
        """Get Qdrant server version.

        Returns:
            Version string

        Raises:
            RuntimeError: If binary is missing or version check fails
        """
        if not self.binary_path.exists():
            raise RuntimeError(f"Qdrant binary not found at {self.binary_path}")

        result = subprocess.run(
            [str(self.binary_path), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Version check failed (code {result.returncode}): {result.stderr}"
            )
        return result.stdout.strip()

    @property
    def is_running(self) -> bool:
        """Check if server is currently running.

        Returns:
            True if running
        """
        return self._process is not None and self._process.poll() is None

    def __enter__(self) -> "QdrantService":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()