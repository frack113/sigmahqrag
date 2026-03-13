"""
Production deployment setup and configuration for SigmaHQ RAG application.
Provides production-ready configuration, monitoring, and deployment utilities.
"""

import json
import logging
import os
import shutil
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
from src.infrastructure.port_manager import PortManager
from src.infrastructure.service_lifecycle import ServiceLifecycleManager
from src.shared.utils import get_app_directory

logger = logging.getLogger("sigmahqrag.production")


@dataclass
class ProductionConfig:
    """Production configuration settings."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    timeout: int = 300

    # Security settings
    enable_cors: bool = True
    allowed_origins: list[str] | None = None
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Performance settings
    max_concurrent_requests: int = 10
    request_timeout: int = 300
    memory_limit_mb: int = 2048
    cpu_limit_percent: float = 80.0

    # Monitoring settings
    health_check_interval: int = 30
    metrics_enabled: bool = True
    log_level: str = "INFO"
    log_file: str = "logs/production.log"

    # Database settings
    db_timeout: int = 30
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # LM Studio settings
    lm_studio_timeout: int = 60
    lm_studio_retries: int = 3
    lm_studio_retry_delay: float = 1.0

    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["*"]


class ProductionSetup:
    """Production deployment setup and configuration manager."""

    def __init__(self, config: ProductionConfig | None = None):
        self.config = config or ProductionConfig()
        self.app_dir = get_app_directory()
        self.port_manager = PortManager()
        self.lifecycle_manager = ServiceLifecycleManager()

        # Monitoring
        self.monitoring_thread = None
        self.monitoring_active = False
        self.system_metrics: list[dict] = []

        # Configuration paths
        self.prod_config_path = self.app_dir / "data" / "config" / "production.json"
        self.deployment_log_path = self.app_dir / "logs" / "deployment.log"

    def setup_production_environment(self) -> bool:
        """Set up the complete production environment."""
        try:
            self._create_production_directories()
            self._configure_logging()
            self._save_production_config()
            self._setup_monitoring()
            self._validate_production_setup()

            logger.info("Production environment setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup production environment: {str(e)}")
            return False

    def _create_production_directories(self):
        """Create necessary production directories."""
        directories = [
            self.app_dir / "logs",
            self.app_dir / "data" / "config",
            self.app_dir / "data" / "cache",
            self.app_dir / "data" / "temp",
            self.app_dir / "data" / "backups",
            self.app_dir / "data" / "monitoring",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _configure_logging(self):
        """Configure production logging."""
        log_file = self.app_dir / self.config.log_file
        
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, self.config.log_level.upper()))
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(getattr(logging, self.config.log_level.upper()))

    def _save_production_config(self):
        """Save production configuration to file."""
        config_data = asdict(self.config)

        with open(self.prod_config_path, "w") as f:
            json.dump(config_data, f, indent=2, default=str)

    def _setup_monitoring(self):
        """Set up system monitoring."""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitor_system_resources, daemon=True
        )
        self.monitoring_thread.start()

    def _monitor_system_resources(self):
        """Monitor system resources in background."""
        while self.monitoring_active:
            try:
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage("/").percent,
                    "process_count": len(psutil.pids()),
                }

                self.system_metrics.append(metrics)

                if metrics["cpu_percent"] > self.config.cpu_limit_percent:
                    logger.warning(f"High CPU usage detected: {metrics['cpu_percent']}%")

                if metrics["memory_percent"] > 90:
                    logger.warning(f"High memory usage detected: {metrics['memory_percent']}%")

                if len(self.system_metrics) > 1000:
                    self.system_metrics.pop(0)

                time.sleep(self.config.health_check_interval)

            except Exception as e:
                logger.error(f"Error in system monitoring: {str(e)}")
                time.sleep(5)

    def _validate_production_setup(self):
        """Validate the production setup."""
        validations = []

        required_dirs = [
            self.app_dir / "logs",
            self.app_dir / "data" / "config",
            self.app_dir / "data" / "cache",
        ]

        for directory in required_dirs:
            if directory.exists():
                validations.append(f"✓ Directory exists: {directory}")
            else:
                validations.append(f"✗ Directory missing: {directory}")

        if self.prod_config_path.exists():
            validations.append("✓ Production config file exists")
        else:
            validations.append("✗ Production config file missing")

        if self.port_manager.is_port_available(self.config.port):
            validations.append(f"✓ Port {self.config.port} is available")
        else:
            validations.append(f"✗ Port {self.config.port} is in use")

        for validation in validations:
            if validation.startswith("✓"):
                logger.info(validation)
            else:
                logger.warning(validation)

    def get_production_config(self) -> ProductionConfig:
        """Get current production configuration."""
        if self.prod_config_path.exists():
            with open(self.prod_config_path) as f:
                config_data = json.load(f)
            return ProductionConfig(**config_data)
        return self.config

    def update_production_config(self, updates: dict[str, Any]) -> bool:
        """Update production configuration."""
        try:
            current_config = self.get_production_config()

            for key, value in updates.items():
                if hasattr(current_config, key):
                    setattr(current_config, key, value)

            self.config = current_config
            self._save_production_config()

            logger.info("Production configuration updated", {"updates": updates})
            return True

        except Exception as e:
            logger.error(f"Failed to update production config: {str(e)}")
            return False

    def get_system_health(self) -> dict[str, Any]:
        """Get current system health status."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            health = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "limit": self.config.cpu_limit_percent,
                    "status": "warning" if cpu_percent > self.config.cpu_limit_percent else "ok",
                },
                "memory": {
                    "percent": memory.percent,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "status": "warning" if memory.percent > 90 else "ok",
                },
                "disk": {
                    "percent": disk.percent,
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "status": "warning" if disk.percent > 90 else "ok",
                },
                "processes": len(psutil.pids()),
                "recent_metrics": self.system_metrics[-10:] if self.system_metrics else [],
            }

            if (
                cpu_percent > self.config.cpu_limit_percent
                or memory.percent > 90
                or disk.percent > 90
            ):
                health["status"] = "warning"

            return health

        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {"status": "error", "error": str(e)}

    def start_production_monitoring(self):
        """Start production monitoring services."""
        if not self.monitoring_active:
            self._setup_monitoring()

    def stop_production_monitoring(self):
        """Stop production monitoring services."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

    def create_deployment_script(self) -> str:
        """Create a deployment script for production."""
        script_content = f'''#!/bin/bash
# SigmaHQ RAG Production Deployment Script
# Generated on {datetime.now().isoformat()}

set -e

echo "Starting SigmaHQ RAG Production Deployment..."

export PYTHONPATH="{self.app_dir}:$PYTHONPATH"
export SIGMAHQ_ENV="production"

mkdir -p {self.app_dir}/logs
mkdir -p {self.app_dir}/data/config
mkdir -p {self.app_dir}/data/cache
mkdir -p {self.app_dir}/data/temp

echo "Installing dependencies..."
uv install --prod

echo "Running database migrations..."
uv run python -m src.infrastructure.database_setup

echo "Validating production setup..."
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup, ProductionConfig

config = ProductionConfig(
    host='{self.config.host}',
    port={self.config.port},
    workers={self.config.workers},
    log_level='{self.config.log_level}'
)
setup = ProductionSetup(config)
if setup.setup_production_environment():
    print('Production setup validated successfully')
else:
    print('Production setup validation failed')
    exit(1)
"

echo "Starting SigmaHQ RAG application..."
uv run python main.py --production

echo "Deployment completed successfully!"
'''

        script_path = self.app_dir / "deploy_production.sh"
        with open(script_path, "w") as f:
            f.write(script_content)

        os.chmod(script_path, 0o755)

        return str(script_path)

    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files."""
        try:
            logs_dir = self.app_dir / "logs"
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)

            cleaned_files = []
            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
                    cleaned_files.append(str(log_file))

            logger.info(f"Cleaned up {len(cleaned_files)} old log files")
        except Exception as e:
            logger.error(f"Error cleaning up logs: {str(e)}")

    def backup_configuration(self) -> str:
        """Create a backup of the current configuration."""
        try:
            backup_dir = self.app_dir / "data" / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"config_backup_{timestamp}.json"

            if self.prod_config_path.exists():
                shutil.copy2(self.prod_config_path, backup_file)

            logger.info(f"Configuration backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return ""

    def create_systemd_service(self) -> str:
        """Create a systemd service file for the application."""
        service_content = f'''[Unit]
Description=SigmaHQ RAG Application
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={self.app_dir}
Environment=PYTHONPATH={self.app_dir}
Environment=SIGMAHQ_ENV=production
ExecStart={self.app_dir}/.venv/bin/uv run python main.py --production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
        return service_content

    def __enter__(self):
        """Context manager entry."""
        self.start_production_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_production_monitoring()


class ProductionDeploymentManager:
    """Manager for production deployments."""

    def __init__(self):
        self.setup = ProductionSetup()
        self.deployment_history: list[dict] = []

    def deploy_to_production(self) -> bool:
        """Deploy the application to production."""
        try:
            deployment_info = {
                "timestamp": datetime.now().isoformat(),
                "status": "in_progress",
                "steps": [],
            }

            deployment_info["steps"].append("Setting up production environment")
            if not self.setup.setup_production_environment():
                deployment_info["status"] = "failed"
                deployment_info["error"] = "Production environment setup failed"
                self.deployment_history.append(deployment_info)
                return False

            script_path = self.setup.create_deployment_script()
            deployment_info["script_path"] = script_path

            health = self.setup.get_system_health()
            if health["status"] != "healthy":
                deployment_info["status"] = "warning"
            else:
                deployment_info["status"] = "success"
                deployment_info["completed_at"] = datetime.now().isoformat()

            self.deployment_history.append(deployment_info)

            logger.info("Production deployment completed", {"status": deployment_info["status"]})
            return deployment_info["status"] == "success"

        except Exception as e:
            logger.error(f"Production deployment failed: {str(e)}")
            return False

    def get_deployment_status(self) -> dict[str, Any]:
        """Get current deployment status."""
        return {
            "current_deployment": self.deployment_history[-1] if self.deployment_history else None,
            "total_deployments": len(self.deployment_history),
            "system_health": self.setup.get_system_health(),
            "production_config": asdict(self.setup.get_production_config()),
        }


def _get_backup_path(backup_dir: Path) -> str:
    """Get path for creating a backup file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(backup_dir / f"config_backup_{timestamp}.json")