"""Llama.cpp server service client."""

import logging
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LlamaService:
    """Manage llama.cpp server subprocess."""

    def __init__(
        self,
        binary_path: Path | str | None = None,
        port: int = 8080,
        host: str = "127.0.0.1",
    ) -> None:
        """Initialize LlamaService.

        Args:
            binary_path: Path to llama-server binary
            port: HTTP server port
            host: HTTP server host
        """
        if binary_path is None:
            from .download import get_binary_path

            binary_path = get_binary_path()

        self.binary_path = Path(binary_path)
        self.port = port
        self.host = host
        self._process: subprocess.Popen[Any] | None = None

        if not self.binary_path.exists():
            logger.warning(
                f"llama.cpp binary not found at {self.binary_path}. "
                "Run download_llama_cpp() first."
            )

    def start(self, model_path: str | Path | None = None) -> subprocess.Popen[Any]:
        """Start llama.cpp server.

        Args:
            model_path: Path to GGUF model file (optional for version check)

        Returns:
            Popen process object

        Raises:
            FileNotFoundError: If binary does not exist
            OSError: If port is already in use
        """
        if not self.binary_path.exists():
            raise FileNotFoundError(
                f"llama.cpp binary not found at {self.binary_path}. "
                "Run download_llama_cpp() first."
            )

        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}. Must be 1-65535.")

        try:
            test_conn = urllib.request.urlopen(
                f"http://{self.host}:{self.port}",
                timeout=1,
            )
            test_conn.close()
            raise OSError(
                f"Port {self.port} is already in use. "
                "Choose a different port or stop the existing service."
            )
        except urllib.error.URLError:
            pass

        if self._process is not None and self._process.poll() is None:
            logger.warning("llama.cpp server already running")
            return self._process

        cmd = [
            str(self.binary_path),
            "--port", str(self.port),
            "--host", self.host,
        ]

        if model_path is not None:
            cmd.extend(["-m", str(model_path)])

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self._wait_for_server(30)

        logger.info(f"llama.cpp server started on {self.host}:{self.port}")
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

        raise TimeoutError("llama.cpp server failed to start within timeout")

    def health_check(self) -> bool:
        """Check if server is running and responsive.

        Returns:
            True if server is healthy
        """
        try:
            request = urllib.request.Request(
                f"http://{self.host}:{self.port}/v1/models",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                status: int = response.status
                return 200 <= status < 300
        except urllib.error.URLError as e:
            logger.debug(f"Health check failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Health check error: {type(e).__name__}: {e}")
            return False

    def stop(self) -> None:
        """Stop llama.cpp server."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None
            logger.info("llama.cpp server stopped")

    def version(self) -> str:
        """Get llama.cpp server version.

        Returns:
            Version string
        """
        result = subprocess.run(
            [str(self.binary_path), "--version"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    @property
    def is_running(self) -> bool:
        """Check if server is currently running.

        Returns:
            True if running
        """
        return self._process is not None and self._process.poll() is None

    def __enter__(self) -> "LlamaService":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()
