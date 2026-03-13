"""
Port Management for SigmaHQ RAG Application

This module provides utilities for managing port allocation and resolving conflicts
for production deployment of the Gradio application.
"""

import logging
import socket
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PortManager:
    """Port management utilities for avoiding conflicts."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """
        Check if a port is available.

        Args:
            port: Port number to check
            host: Host to check (default: localhost)

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0
        except Exception as e:
            self.logger.error(f"Error checking port {port}: {e}")
            return False

    def find_available_port(
        self, start_port: int, max_attempts: int = 10, host: str = "localhost"
    ) -> int | None:
        """
        Find an available port starting from a given port.

        Args:
            start_port: Starting port number
            max_attempts: Maximum number of ports to try
            host: Host to check (default: localhost)

        Returns:
            Available port number or None if none found
        """
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(port, host):
                self.logger.info(f"Found available port: {port}")
                return port

        self.logger.warning(
            f"No available port found in range {start_port}-{start_port + max_attempts - 1}"
        )
        return None

    def check_common_ports(self) -> dict[str, bool]:
        """
        Check status of common ports used by the application.

        Returns:
            Dictionary with port status
        """
        common_ports = {
            "lm_studio": 1234,
            "gradio_default": 7860,
            "gradio_alternate": 8000,
            "gradio_production": 8080,
            "gradio_dev": 3000,
        }

        port_status = {}
        for service, port in common_ports.items():
            port_status[service] = self.is_port_available(port)

        return port_status

    def get_production_config(self) -> dict[str, int]:
        """
        Get production-ready port configuration.

        Returns:
            Dictionary with production port configuration
        """
        # Check if default ports are available
        port_status = self.check_common_ports()

        config = {}

        # LM Studio should be on 1234 (already running)
        if not port_status["lm_studio"]:
            self.logger.warning("LM Studio port 1234 is in use")

        # Find available port for Gradio
        gradio_port = None

        # Try preferred production ports first
        preferred_ports = [8080, 8000, 7860, 3000]

        for port in preferred_ports:
            if self.is_port_available(port):
                gradio_port = port
                break

        # If no preferred port available, find next available
        if gradio_port is None:
            gradio_port = self.find_available_port(8080, 20)

        if gradio_port:
            config["gradio_port"] = gradio_port
            self.logger.info(f"Selected Gradio port: {gradio_port}")
        else:
            self.logger.error("No available port found for Gradio")
            config["gradio_port"] = 7860  # Fallback

        # LM Studio port
        config["lm_studio_port"] = 1234

        return config

    def create_port_config(self, config_path: str = "data/config/ports.json") -> bool:
        """
        Create port configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if config created successfully, False otherwise
        """
        config_dir = Path(config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)

        port_config = self.get_production_config()

        config = {
            "gradio": {
                "port": port_config["gradio_port"],
                "host": "0.0.0.0",
                "share": False,
                "debug": False,
            },
            "lm_studio": {"port": port_config["lm_studio_port"], "host": "localhost"},
            "fallback_ports": [8080, 8000, 7860, 3000, 9000, 9001],
        }

        try:
            with open(config_path, "w") as f:
                import json

                json.dump(config, f, indent=2)
            self.logger.info(f"Port config created at: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating port config: {e}")
            return False

    def validate_port_configuration(self) -> dict[str, Any]:
        """
        Validate the current port configuration.

        Returns:
            Dictionary with validation results
        """
        results = {
            "lm_studio_accessible": False,
            "gradio_port_available": False,
            "recommended_gradio_port": None,
            "conflicts": [],
        }

        # Check LM Studio
        lm_studio_port = 1234
        results["lm_studio_accessible"] = not self.is_port_available(lm_studio_port)

        # Check Gradio ports
        port_status = self.check_common_ports()

        for service, available in port_status.items():
            if service.startswith("gradio") and not available:
                results["conflicts"].append(f"Port {port_status[service]} is in use")

        # Find recommended port
        results["recommended_gradio_port"] = self.find_available_port(8080, 20)

        if results["recommended_gradio_port"]:
            results["gradio_port_available"] = True

        return results


def create_port_management_config() -> dict[str, Any]:
    """
    Create port management configuration.

    Returns:
        Dictionary with port management results
    """
    port_manager = PortManager()

    # Create port config
    config_created = port_manager.create_port_config()

    # Validate configuration
    validation = port_manager.validate_port_configuration()

    results = {
        "config_created": config_created,
        "lm_studio_accessible": validation["lm_studio_accessible"],
        "gradio_port_available": validation["gradio_port_available"],
        "recommended_gradio_port": validation["recommended_gradio_port"],
        "conflicts": validation["conflicts"],
    }

    return results


if __name__ == "__main__":
    # Test port management
    results = create_port_management_config()
    print("Port Management Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")
