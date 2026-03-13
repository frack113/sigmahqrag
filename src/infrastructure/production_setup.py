"""
Production deployment setup and configuration for SigmaHQ RAG application.
Provides production-ready configuration, monitoring, and deployment utilities.
"""

import os
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import psutil
import threading
from contextlib import contextmanager

from src.shared.constants import (
    DEFAULT_LOG_LEVEL, 
    DEFAULT_LOG_FILE, 
    DEFAULT_LOG_FORMAT,
    DEFAULT_SERVER_PORT,
    DEFAULT_SERVER_HOST
)
from src.shared.utils import get_app_directory
from src.infrastructure.port_manager import PortManager
from src.infrastructure.service_lifecycle import ServiceLifecycleManager
from src.models.logging_service import LoggingService


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
    allowed_origins: List[str] = None
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
    
    def __init__(self, config: ProductionConfig = None):
        self.config = config or ProductionConfig()
        self.app_dir = get_app_directory()
        self.port_manager = PortManager()
        self.lifecycle_manager = ServiceLifecycleManager()
        self.logging_service = LoggingService()
        
        # Monitoring
        self.monitoring_thread = None
        self.monitoring_active = False
        self.system_metrics = []
        
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
            
            self.logging_service.log_info(
                "Production environment setup completed successfully",
                {"config": asdict(self.config)}
            )
            return True
            
        except Exception as e:
            self.logging_service.log_error(
                f"Failed to setup production environment: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def _create_production_directories(self):
        """Create necessary production directories."""
        directories = [
            self.app_dir / "logs",
            self.app_dir / "data" / "config",
            self.app_dir / "data" / "cache",
            self.app_dir / "data" / "temp",
            self.app_dir / "data" / "backups",
            self.app_dir / "data" / "monitoring"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        self.logging_service.log_info(
            "Production directories created",
            {"directories": [str(d) for d in directories]}
        )
    
    def _configure_logging(self):
        """Configure production logging."""
        # Create production logger
        logger = logging.getLogger("sigmahqrag.production")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # File handler for production logs
        log_file = self.app_dir / self.config.log_file
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Console handler for critical errors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        self.logging_service.log_info("Production logging configured")
    
    def _save_production_config(self):
        """Save production configuration to file."""
        config_data = asdict(self.config)
        
        with open(self.prod_config_path, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
            
        self.logging_service.log_info(
            "Production configuration saved",
            {"path": str(self.prod_config_path)}
        )
    
    def _setup_monitoring(self):
        """Set up system monitoring."""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitor_system_resources,
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logging_service.log_info("System monitoring started")
    
    def _monitor_system_resources(self):
        """Monitor system resources in background."""
        while self.monitoring_active:
            try:
                # Get system metrics
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'process_count': len(psutil.pids()),
                    'network_io': psutil.net_io_counters()._asdict()
                }
                
                self.system_metrics.append(metrics)
                
                # Log warnings if thresholds exceeded
                if metrics['cpu_percent'] > self.config.cpu_limit_percent:
                    self.logging_service.log_warning(
                        f"High CPU usage detected: {metrics['cpu_percent']}%"
                    )
                
                if metrics['memory_percent'] > 90:
                    self.logging_service.log_warning(
                        f"High memory usage detected: {metrics['memory_percent']}%"
                    )
                
                # Keep only last 1000 metrics
                if len(self.system_metrics) > 1000:
                    self.system_metrics.pop(0)
                    
                time.sleep(self.config.health_check_interval)
                
            except Exception as e:
                self.logging_service.log_error(
                    f"Error in system monitoring: {str(e)}"
                )
                time.sleep(5)  # Wait before retrying
    
    def _validate_production_setup(self):
        """Validate the production setup."""
        validations = []
        
        # Check if required directories exist
        required_dirs = [
            self.app_dir / "logs",
            self.app_dir / "data" / "config",
            self.app_dir / "data" / "cache"
        ]
        
        for directory in required_dirs:
            if directory.exists():
                validations.append(f"✓ Directory exists: {directory}")
            else:
                validations.append(f"✗ Directory missing: {directory}")
        
        # Check if production config exists
        if self.prod_config_path.exists():
            validations.append("✓ Production config file exists")
        else:
            validations.append("✗ Production config file missing")
        
        # Check port availability
        if self.port_manager.is_port_available(self.config.port):
            validations.append(f"✓ Port {self.config.port} is available")
        else:
            validations.append(f"✗ Port {self.config.port} is in use")
        
        # Log validation results
        for validation in validations:
            if validation.startswith("✓"):
                self.logging_service.log_info(validation)
            else:
                self.logging_service.log_warning(validation)
    
    def get_production_config(self) -> ProductionConfig:
        """Get current production configuration."""
        if self.prod_config_path.exists():
            with open(self.prod_config_path, 'r') as f:
                config_data = json.load(f)
            return ProductionConfig(**config_data)
        return self.config
    
    def update_production_config(self, updates: Dict[str, Any]) -> bool:
        """Update production configuration."""
        try:
            current_config = self.get_production_config()
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(current_config, key):
                    setattr(current_config, key, value)
            
            # Save updated config
            self.config = current_config
            self._save_production_config()
            
            self.logging_service.log_info(
                "Production configuration updated",
                {"updates": updates}
            )
            return True
            
        except Exception as e:
            self.logging_service.log_error(
                f"Failed to update production config: {str(e)}"
            )
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            # Get current system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'limit': self.config.cpu_limit_percent,
                    'status': 'warning' if cpu_percent > self.config.cpu_limit_percent else 'ok'
                },
                'memory': {
                    'percent': memory.percent,
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'status': 'warning' if memory.percent > 90 else 'ok'
                },
                'disk': {
                    'percent': disk.percent,
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'status': 'warning' if disk.percent > 90 else 'ok'
                },
                'processes': len(psutil.pids()),
                'recent_metrics': self.system_metrics[-10:] if self.system_metrics else []
            }
            
            # Determine overall status
            if (cpu_percent > self.config.cpu_limit_percent or 
                memory.percent > 90 or 
                disk.percent > 90):
                health['status'] = 'warning'
            
            return health
            
        except Exception as e:
            self.logging_service.log_error(f"Error getting system health: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
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

# Set environment variables
export PYTHONPATH="{self.app_dir}:$PYTHONPATH"
export SIGMAHQ_ENV="production"

# Create necessary directories
mkdir -p {self.app_dir}/logs
mkdir -p {self.app_dir}/data/config
mkdir -p {self.app_dir}/data/cache
mkdir -p {self.app_dir}/data/temp

# Install dependencies
echo "Installing dependencies..."
uv install --prod

# Run database migrations
echo "Running database migrations..."
uv run python -m src.infrastructure.database_setup

# Validate production setup
echo "Validating production setup..."
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
from src.shared.constants import ProductionConfig

config = ProductionConfig(
    host='{self.config.host}',
    port={self.config.port},
    workers={self.config.workers},
    log_level='{self.config.log_level}'
)
setup = ProductionSetup(config)
if setup.setup_production_environment():
    print("✓ Production setup validated successfully")
else:
    print("✗ Production setup validation failed")
    exit(1)
"

# Start LM Studio server
echo "Starting LM Studio server..."
uv run python -m src.infrastructure.lm_studio_setup

# Start the application
echo "Starting SigmaHQ RAG application..."
uv run python main.py --production

echo "Deployment completed successfully!"
'''
        
        script_path = self.app_dir / "deploy_production.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        self.logging_service.log_info(
            "Production deployment script created",
            {"path": str(script_path)}
        )
        
        return str(script_path)
    
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

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths={self.app_dir}

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
'''
        
        service_path = f"/etc/systemd/system/sigmahqrag.service"
        
        # Note: This would typically require sudo privileges
        self.logging_service.log_info(
            "Systemd service file content generated",
            {"content": service_content}
        )
        
        return service_content
    
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
            
            if cleaned_files:
                self.logging_service.log_info(
                    f"Cleaned up {len(cleaned_files)} old log files"
                )
            else:
                self.logging_service.log_info("No old log files to clean up")
                
        except Exception as e:
            self.logging_service.log_error(f"Error cleaning up logs: {str(e)}")
    
    def backup_configuration(self) -> str:
        """Create a backup of the current configuration."""
        try:
            backup_dir = self.app_dir / "data" / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"config_backup_{timestamp}.json"
            
            # Backup production config
            if self.prod_config_path.exists():
                import shutil
                shutil.copy2(self.prod_config_path, backup_file)
            
            # Backup system metrics
            metrics_backup = backup_dir / f"metrics_backup_{timestamp}.json"
            with open(metrics_backup, 'w') as f:
                json.dump(self.system_metrics, f, indent=2)
            
            self.logging_service.log_info(
                "Configuration backup created",
                {"backup_file": str(backup_file)}
            )
            
            return str(backup_file)
            
        except Exception as e:
            self.logging_service.log_error(f"Error creating backup: {str(e)}")
            return ""
    
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
        self.deployment_history = []
    
    def deploy_to_production(self) -> bool:
        """Deploy the application to production."""
        try:
            deployment_info = {
                'timestamp': datetime.now().isoformat(),
                'status': 'in_progress',
                'steps': []
            }
            
            # Step 1: Setup production environment
            deployment_info['steps'].append('Setting up production environment')
            if not self.setup.setup_production_environment():
                deployment_info['status'] = 'failed'
                deployment_info['error'] = 'Production environment setup failed'
                self.deployment_history.append(deployment_info)
                return False
            
            # Step 2: Create deployment script
            deployment_info['steps'].append('Creating deployment script')
            script_path = self.setup.create_deployment_script()
            
            # Step 3: Validate deployment
            deployment_info['steps'].append('Validating deployment')
            health = self.setup.get_system_health()
            if health['status'] in ['error', 'warning']:
                deployment_info['status'] = 'warning'
                deployment_info['health_warnings'] = health
            else:
                deployment_info['status'] = 'success'
            
            deployment_info['script_path'] = script_path
            deployment_info['completed_at'] = datetime.now().isoformat()
            
            self.deployment_history.append(deployment_info)
            
            self.setup.logging_service.log_info(
                "Production deployment completed",
                {"status": deployment_info['status']}
            )
            
            return deployment_info['status'] == 'success'
            
        except Exception as e:
            self.setup.logging_service.log_error(
                f"Production deployment failed: {str(e)}"
            )
            return False
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        return {
            'current_deployment': self.deployment_history[-1] if self.deployment_history else None,
            'total_deployments': len(self.deployment_history),
            'system_health': self.setup.get_system_health(),
            'production_config': asdict(self.setup.get_production_config())
        }