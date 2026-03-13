"""
Service Lifecycle Management

This module provides utilities for managing the lifecycle of services
in the SigmaHQ RAG application, including startup, shutdown, and health monitoring.
"""

import logging
import signal
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)


class ServiceLifecycleManager:
    """Service lifecycle management utilities."""

    def __init__(self):
        """
        Initialize service lifecycle manager.
        """
        self.services = {}
        self.running = False
        self.shutdown_event = threading.Event()
        self.health_checks = {}
        self.startup_callbacks = []
        self.shutdown_callbacks = []
        self.logger = logging.getLogger(__name__)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def register_service(
        self,
        name: str,
        service_instance: Any,
        health_check: Callable[[], bool] | None = None,
        startup_callback: Callable[[], None] | None = None,
        shutdown_callback: Callable[[], None] | None = None,
    ) -> bool:
        """
        Register a service with the lifecycle manager.

        Args:
            name: Service name
            service_instance: Service instance
            health_check: Optional health check function
            startup_callback: Optional startup callback
            shutdown_callback: Optional shutdown callback

        Returns:
            True if service registered successfully
        """
        try:
            self.services[name] = {
                "instance": service_instance,
                "status": "registered",
                "startup_time": None,
                "last_health_check": None,
                "health_status": None,
            }

            if health_check:
                self.health_checks[name] = health_check

            if startup_callback:
                self.startup_callbacks.append(startup_callback)

            if shutdown_callback:
                self.shutdown_callbacks.append(shutdown_callback)

            self.logger.info(f"Service registered: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register service {name}: {e}")
            return False

    def start_service(self, name: str) -> bool:
        """
        Start a registered service.

        Args:
            name: Service name

        Returns:
            True if service started successfully
        """
        try:
            if name not in self.services:
                self.logger.error(f"Service not registered: {name}")
                return False

            service_info = self.services[name]

            if service_info["status"] in ["running", "starting"]:
                self.logger.warning(f"Service already running: {name}")
                return True

            self.logger.info(f"Starting service: {name}")
            service_info["status"] = "starting"
            service_info["startup_time"] = time.time()

            # Call service start method if it exists
            service_instance = service_info["instance"]
            if hasattr(service_instance, "start"):
                service_instance.start()
            elif hasattr(service_instance, "run"):
                # For services that run in their own thread
                if hasattr(service_instance, "daemon") or hasattr(
                    service_instance, "start"
                ):
                    service_instance.start()

            service_info["status"] = "running"
            self.logger.info(f"Service started successfully: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start service {name}: {e}")
            service_info["status"] = "error"
            return False

    def stop_service(self, name: str) -> bool:
        """
        Stop a running service.

        Args:
            name: Service name

        Returns:
            True if service stopped successfully
        """
        try:
            if name not in self.services:
                self.logger.error(f"Service not registered: {name}")
                return False

            service_info = self.services[name]

            if service_info["status"] not in ["running", "starting"]:
                self.logger.warning(f"Service not running: {name}")
                return True

            self.logger.info(f"Stopping service: {name}")
            service_info["status"] = "stopping"

            # Call service stop method if it exists
            service_instance = service_info["instance"]
            if hasattr(service_instance, "stop"):
                service_instance.stop()
            elif hasattr(service_instance, "shutdown"):
                service_instance.shutdown()
            elif hasattr(service_instance, "close"):
                service_instance.close()

            service_info["status"] = "stopped"
            self.logger.info(f"Service stopped successfully: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop service {name}: {e}")
            return False

    def start_all_services(self) -> dict[str, bool]:
        """
        Start all registered services.

        Returns:
            Dictionary with start results for each service
        """
        results = {}

        self.logger.info("Starting all services...")

        for service_name in self.services.keys():
            results[service_name] = self.start_service(service_name)

        # Run startup callbacks
        for callback in self.startup_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Startup callback failed: {e}")

        return results

    def stop_all_services(self) -> dict[str, bool]:
        """
        Stop all running services.

        Returns:
            Dictionary with stop results for each service
        """
        results = {}

        self.logger.info("Stopping all services...")

        # Run shutdown callbacks first
        for callback in self.shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Shutdown callback failed: {e}")

        # Stop services in reverse order
        for service_name in reversed(list(self.services.keys())):
            results[service_name] = self.stop_service(service_name)

        return results

    def check_service_health(self, name: str) -> bool | None:
        """
        Check the health of a service.

        Args:
            name: Service name

        Returns:
            Health status (True=healthy, False=unhealthy, None=unknown)
        """
        try:
            if name not in self.services:
                return None

            service_info = self.services[name]

            if name in self.health_checks:
                health_check = self.health_checks[name]
                health_status = health_check()
                service_info["health_status"] = health_status
                service_info["last_health_check"] = time.time()
                return health_status

            # Default health check based on service status
            return service_info["status"] == "running"

        except Exception as e:
            self.logger.error(f"Health check failed for service {name}: {e}")
            return False

    def check_all_services_health(self) -> dict[str, bool]:
        """
        Check the health of all services.

        Returns:
            Dictionary with health status for each service
        """
        health_status = {}

        for service_name in self.services.keys():
            health_status[service_name] = (
                self.check_service_health(service_name) or False
            )

        return health_status

    def get_service_status(self, name: str) -> dict[str, Any] | None:
        """
        Get the status of a service.

        Args:
            name: Service name

        Returns:
            Service status information or None if service not found
        """
        if name in self.services:
            return self.services[name].copy()
        return None

    def get_all_services_status(self) -> dict[str, dict[str, Any]]:
        """
        Get the status of all services.

        Returns:
            Dictionary with status information for each service
        """
        return {name: info.copy() for name, info in self.services.items()}

    def get_service_uptime(self, name: str) -> float | None:
        """
        Get the uptime of a service.

        Args:
            name: Service name

        Returns:
            Uptime in seconds or None if service not found or not started
        """
        if name in self.services:
            service_info = self.services[name]
            if service_info["startup_time"]:
                return time.time() - service_info["startup_time"]
        return None

    def is_running(self) -> bool:
        """
        Check if the lifecycle manager is running.

        Returns:
            True if running
        """
        return self.running

    def start(self) -> bool:
        """
        Start the lifecycle manager and all services.

        Returns:
            True if started successfully
        """
        try:
            self.logger.info("Starting service lifecycle manager...")
            self.running = True
            self.shutdown_event.clear()

            # Start all services
            start_results = self.start_all_services()

            # Check if all services started successfully
            all_started = all(start_results.values())

            if all_started:
                self.logger.info("Service lifecycle manager started successfully")
                return True
            else:
                self.logger.error("Some services failed to start")
                return False

        except Exception as e:
            self.logger.error(f"Failed to start lifecycle manager: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop the lifecycle manager and all services.

        Returns:
            True if stopped successfully
        """
        try:
            self.logger.info("Stopping service lifecycle manager...")
            self.running = False
            self.shutdown_event.set()

            # Stop all services
            stop_results = self.stop_all_services()

            # Check if all services stopped successfully
            all_stopped = all(stop_results.values())

            if all_stopped:
                self.logger.info("Service lifecycle manager stopped successfully")
                return True
            else:
                self.logger.error("Some services failed to stop")
                return False

        except Exception as e:
            self.logger.error(f"Failed to stop lifecycle manager: {e}")
            return False

    def wait_for_shutdown(self, timeout: float | None = None) -> bool:
        """
        Wait for shutdown signal.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if shutdown signal received
        """
        try:
            self.logger.info("Waiting for shutdown signal...")
            return self.shutdown_event.wait(timeout)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            return True

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Signal frame
        """
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()

    @contextmanager
    def lifecycle_context(self):
        """
        Context manager for service lifecycle.
        """
        try:
            if self.start():
                yield self
            else:
                yield None
        finally:
            self.stop()

    def get_lifecycle_summary(self) -> dict[str, Any]:
        """
        Get a summary of the lifecycle manager state.

        Returns:
            Dictionary with lifecycle summary
        """
        summary = {
            "running": self.running,
            "services_count": len(self.services),
            "services": {},
            "health_status": {},
            "total_uptime": 0,
        }

        # Get service details
        for service_name, service_info in self.services.items():
            summary["services"][service_name] = {
                "status": service_info["status"],
                "startup_time": service_info["startup_time"],
                "last_health_check": service_info["last_health_check"],
                "health_status": service_info["health_status"],
            }

        # Get health status
        summary["health_status"] = self.check_all_services_health()

        # Calculate total uptime
        uptimes = [self.get_service_uptime(name) for name in self.services.keys()]
        summary["total_uptime"] = sum(
            uptime for uptime in uptimes if uptime is not None
        )

        return summary


def create_service_lifecycle_manager() -> ServiceLifecycleManager:
    """
    Create a service lifecycle manager instance.

    Returns:
        ServiceLifecycleManager instance
    """
    return ServiceLifecycleManager()


if __name__ == "__main__":
    # Test service lifecycle manager
    lifecycle_manager = create_service_lifecycle_manager()

    # Create mock services
    class MockService:
        def __init__(self, name):
            self.name = name
            self.running = False

        def start(self):
            self.running = True
            print(f"MockService {self.name} started")

        def stop(self):
            self.running = False
            print(f"MockService {self.name} stopped")

    # Register services
    service1 = MockService("test_service_1")
    service2 = MockService("test_service_2")

    lifecycle_manager.register_service("service1", service1)
    lifecycle_manager.register_service("service2", service2)

    # Start lifecycle manager
    if lifecycle_manager.start():
        print("Lifecycle manager started successfully")

        # Check status
        status = lifecycle_manager.get_lifecycle_summary()
        print(
            f"Services running: {len([s for s in status['services'].values() if s['status'] == 'running'])}"
        )

        # Wait a moment
        time.sleep(2)

        # Stop lifecycle manager
        lifecycle_manager.stop()
        print("Lifecycle manager stopped")
    else:
        print("Failed to start lifecycle manager")
