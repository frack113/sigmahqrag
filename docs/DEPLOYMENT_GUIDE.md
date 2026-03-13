# SigmaHQ RAG - Production Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying the SigmaHQ RAG application to production environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Production Environment Setup](#production-environment-setup)
3. [Configuration](#configuration)
4. [Deployment Methods](#deployment-methods)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)
6. [Troubleshooting](#troubleshooting)
7. [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+, or equivalent)
- **Python**: 3.10 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 10GB available disk space
- **Network**: Internet access for dependency installation

### Dependencies
- **uv**: Python package manager and virtual environment tool
- **LM Studio**: Local LLM server (optional but recommended)
- **Git**: For version control and deployment

### Installation
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Git (if not already installed)
# Ubuntu/Debian:
sudo apt update && sudo apt install git

# CentOS/RHEL:
sudo yum install git
```

## Production Environment Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd sigmahqrag
```

### 2. Install Dependencies
```bash
# Install production dependencies
uv install --prod

# Install optional dependencies for production
uv add --prod psutil  # For system monitoring
```

### 3. Setup Production Environment
```bash
# Setup production environment only (no app start)
uv run python main.py --production --setup-only

# This will:
# - Create necessary directories
# - Configure production logging
# - Validate system requirements
# - Create production configuration
```

### 4. Configure Production Settings
Edit `data/config/production.json` to customize production settings:

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "workers": 1,
  "timeout": 300,
  "enable_cors": true,
  "allowed_origins": ["*"],
  "rate_limit_enabled": true,
  "rate_limit_requests": 100,
  "rate_limit_window": 60,
  "max_concurrent_requests": 10,
  "request_timeout": 300,
  "memory_limit_mb": 2048,
  "cpu_limit_percent": 80.0,
  "health_check_interval": 30,
  "metrics_enabled": true,
  "log_level": "INFO",
  "log_file": "logs/production.log",
  "db_timeout": 30,
  "db_pool_size": 10,
  "db_max_overflow": 20,
  "lm_studio_timeout": 60,
  "lm_studio_retries": 3,
  "lm_studio_retry_delay": 1.0
}
```

## Configuration

### Environment Variables
Set these environment variables for production:

```bash
export SIGMAHQ_ENV="production"
export PYTHONPATH="/path/to/sigmahqrag:$PYTHONPATH"
export UV_PROJECT_ENVIRONMENT="production"
```

### Database Configuration
The application uses SQLite by default. For production, consider:

1. **SQLite** (Default): Simple, file-based database
2. **PostgreSQL**: For high-availability setups
3. **MySQL**: Alternative relational database

### LM Studio Configuration
Configure LM Studio for production:

1. Install LM Studio server
2. Configure models for production use
3. Set appropriate resource limits
4. Configure network access

## Deployment Methods

### Method 1: Manual Deployment

#### Step 1: Setup
```bash
# Navigate to application directory
cd /opt/sigmahqrag

# Setup production environment
uv run python main.py --production --setup-only
```

#### Step 2: Start Application
```bash
# Start in production mode
uv run python main.py --production --host 0.0.0.0 --port 8000
```

#### Step 3: Verify Deployment
```bash
# Check application health
curl http://localhost:8000/health

# Check system resources
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
print(setup.get_system_health())
"
```

### Method 2: Using Deployment Script

#### Generate Deployment Script
```bash
# Create deployment script
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
script_path = setup.create_deployment_script()
print(f'Deployment script created at: {script_path}')
"
```

#### Run Deployment Script
```bash
# Make script executable
chmod +x deploy_production.sh

# Run deployment
./deploy_production.sh
```

### Method 3: Systemd Service

#### Create Systemd Service
```bash
# Generate systemd service configuration
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
service_content = setup.create_systemd_service()
print(service_content)
" > /etc/systemd/system/sigmahqrag.service
```

#### Configure and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable sigmahqrag

# Start service
sudo systemctl start sigmahqrag

# Check status
sudo systemctl status sigmahqrag
```

### Method 4: Docker Deployment

#### Create Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy application
COPY . .

# Install dependencies
RUN uv install --prod

# Setup production environment
RUN uv run python main.py --production --setup-only

# Expose port
EXPOSE 8000

# Start application
CMD ["uv", "run", "python", "main.py", "--production"]
```

#### Build and Run
```bash
# Build image
docker build -t sigmahqrag:production .

# Run container
docker run -d \
  --name sigmahqrag \
  -p 8000:8000 \
  -v /path/to/data:/app/data \
  -v /path/to/logs:/app/logs \
  sigmahqrag:production
```

## Monitoring and Maintenance

### System Monitoring
The application includes built-in monitoring:

```bash
# Check system health
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
health = setup.get_system_health()
print(f'System Status: {health[\"status\"]}')
print(f'CPU Usage: {health[\"cpu\"][\"percent\"]}%')
print(f'Memory Usage: {health[\"memory\"][\"percent\"]}%')
print(f'Disk Usage: {health[\"disk\"][\"percent\"]}%')
"
```

### Log Monitoring
```bash
# View production logs
tail -f logs/production.log

# View deployment logs
tail -f logs/deployment.log

# Search for errors
grep ERROR logs/production.log
```

### Performance Monitoring
```bash
# Monitor resource usage
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
metrics = setup.get_system_health()
print(f'Process Count: {metrics[\"processes\"]}')
print(f'Recent Metrics: {len(metrics[\"recent_metrics\"])} entries')
"
```

### Maintenance Tasks

#### Log Rotation
```bash
# Clean up old logs (keep 30 days)
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
setup.cleanup_old_logs(days_to_keep=30)
"
```

#### Configuration Backup
```bash
# Create configuration backup
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
backup_file = setup.backup_configuration()
print(f'Configuration backed up to: {backup_file}')
"
```

#### Database Maintenance
```bash
# Run database maintenance
uv run python -m src.infrastructure.database_setup --maintenance
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
sudo netstat -tlnp | grep :8000

# Kill the process
sudo kill -9 <PID>

# Or use a different port
uv run python main.py --production --port 8001
```

#### Permission Denied
```bash
# Check file permissions
ls -la data/ logs/

# Fix permissions
sudo chown -R $USER:$USER data/ logs/
sudo chmod -R 755 data/ logs/
```

#### Dependency Issues
```bash
# Reinstall dependencies
uv pip uninstall -r requirements.txt
uv install --prod

# Check Python path
echo $PYTHONPATH
```

#### LM Studio Connection Issues
```bash
# Check LM Studio status
curl http://localhost:1234/v1/models

# Restart LM Studio
systemctl restart lm-studio

# Check configuration
cat data/config/lm_studio.json
```

### Debug Mode
```bash
# Start with debug logging
uv run python main.py --production --log-level DEBUG

# Enable verbose output
LOG_LEVEL=DEBUG uv run python main.py --production
```

### Health Checks
```bash
# Application health endpoint
curl http://localhost:8000/health

# Database health
uv run python -c "
from src.infrastructure.database_setup import DatabaseManager
db = DatabaseManager()
print(f'Database Status: {db.get_health_status()}')
"

# LM Studio health
curl http://localhost:1234/v1/health
```

## Security Considerations

### Network Security
- Use HTTPS in production
- Configure firewall rules
- Restrict access to management ports
- Use VPN for remote access

### Application Security
- Keep dependencies updated
- Use strong authentication
- Implement rate limiting
- Monitor for suspicious activity

### Data Security
- Encrypt sensitive data
- Regular backups
- Secure file permissions
- Audit access logs

### Production Checklist
- [ ] Change default passwords
- [ ] Configure HTTPS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Test disaster recovery
- [ ] Review security settings
- [ ] Update firewall rules
- [ ] Monitor logs regularly

## Performance Optimization

### Application Tuning
```json
{
  "workers": 2,
  "max_concurrent_requests": 20,
  "memory_limit_mb": 4096,
  "cpu_limit_percent": 90.0,
  "request_timeout": 600
}
```

### Database Optimization
- Use connection pooling
- Optimize queries
- Regular maintenance
- Consider read replicas

### Caching Strategy
- Implement response caching
- Use CDN for static assets
- Cache expensive computations
- Optimize LLM responses

### Monitoring and Alerting
Set up alerts for:
- High CPU/memory usage
- Application errors
- Database issues
- Network problems

## Support and Maintenance

### Regular Tasks
- **Daily**: Check logs and system health
- **Weekly**: Review performance metrics
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and update configurations

### Emergency Procedures
1. **Application Down**: Check logs, restart services
2. **Database Issues**: Check connections, run maintenance
3. **Security Incident**: Isolate system, investigate, patch
4. **Performance Issues**: Monitor resources, optimize queries

### Contact Information
- **Development Team**: [contact details]
- **Operations Team**: [contact details]
- **Emergency Support**: [contact details]

## Conclusion
This deployment guide provides comprehensive instructions for deploying SigmaHQ RAG to production. Always test deployments in a staging environment first, and maintain regular backups and monitoring for production systems.