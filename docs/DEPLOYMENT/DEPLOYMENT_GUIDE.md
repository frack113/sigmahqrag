# SigmaHQ RAG - Production Deployment Guide

This guide provides comprehensive instructions for deploying the SigmaHQ RAG application to production environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Production Setup](#production-setup)
3. [Configuration](#configuration)
4. [Deployment Methods](#deployment-methods)
5. [Monitoring and Maintenance](#monitoring-and-maintenance)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+, or equivalent)
- **Python**: 3.10 or higher
- **Memory**: Minimum 2GB RAM
- **Storage**: 5GB available disk space
- **Network**: Internet access for dependency installation

### Dependencies
- **uv**: Python package manager (installed via installer)
- **LM Studio**: Local LLM server (optional but recommended)
- **Git**: For version control

### Installation
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <repository-url>
cd sigmahqrag
```

## Production Setup

### 1. Basic Setup
```bash
# Install production dependencies
uv install --prod

# Setup production environment (no app start)
uv run python main.py --setup-only
```

### 2. Edit Configuration
Edit `data/config.json`:

```json
{
  "application": {
    "name": "SigmaHQ RAG",
    "version": "1.0.0"
  },
  "network": {
    "ip": "0.0.0.0",
    "port": 8000,
    "timeout": 30
  },
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000,
    "base_url": "http://localhost:1234"
  }
}
```

### 3. Start Application
```bash
# Start in production mode
uv run python main.py

# Start with custom port
uv run python main.py --port 8001

# Setup only (no app start)
uv run python main.py --setup-only
```

## Configuration

### Network Settings (`data/config.json`)
```json
{
  "network": {
    "ip": "0.0.0.0",
    "port": 8000,
    "timeout": 30
  }
}
```

### LLM Configuration
```json
{
  "llm": {
    "base_url": "http://localhost:1234",
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000
  }
}
```

### LM Studio Settings
- **Server URL**: `http://localhost:1234`
- **Model**: Available in LM Studio interface
- **Fallback**: CPU-based embeddings via sentence-transformers

## Deployment Methods

### Method 1: Manual Startup (Development/Staging)
```bash
# Start with default settings
uv run python main.py

# Start with custom port
uv run python main.py --port 8001

# Verify application is running
curl http://localhost:8000/health
```

### Method 2: Systemd Service (Production)

#### Create Systemd Service File
```bash
sudo tee /etc/systemd/system/sigmahqrag.service > /dev/null <<'EOF'
[Unit]
Description=SigmaHQ RAG Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/sigmahqrag
Environment="PYTHONPATH=/path/to/sigmahqrag"
Environment="UV_PROJECT_ENVIRONMENT=/path/to/sigmahqrag"
ExecStart=/path/to/uv run python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
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

### Method 3: Docker Deployment

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

# Expose port
EXPOSE 8000

# Start application
CMD ["uv", "run", "python", "main.py"]
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
  sigmahqrag:production
```

## Monitoring and Maintenance

### Check System Health
```bash
# Get application health status
curl http://localhost:8000/health
```

### View Logs
```bash
# Development mode logs (stdout)
# Production logs via systemd journal
sudo journalctl -u sigmahqrag -f

# Or use logs directory
tail -f logs/*.log
```

### Restart Service
```bash
sudo systemctl restart sigmahqrag
sudo systemctl status sigmahqrag
```

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uv run python main.py --port 8001
```

### LM Studio Connection Issues
```bash
# Check if LM Studio is running
curl http://localhost:1234/v1/models

# Restart LM Studio service (if installed as service)
sudo systemctl restart lm-studio
```

### Application Won't Start
```bash
# Check logs for errors
tail -n 50 logs/sigmahqrag.log

# Verify Python path
echo $PYTHONPATH

# Check uv installation
uv --version
```

### Database Issues
The application uses SQLite at `data/history/rag_history.db`:
- Ensure the directory exists
- Check file permissions
- Monitor database size for large deployments

## Security Considerations

### Network Security
- Use HTTPS in production
- Configure firewall rules
- Restrict access to management ports

### Application Security
- Keep dependencies updated: `uv update`
- Regular security audits
- Monitor for suspicious activity

### Data Security
- Set appropriate file permissions
- Backup configuration files
- Secure sensitive data at rest

## Support

- **Logs**: Check logs directory or systemd journal
- **Configuration**: Review `data/config.json`
- **Documentation**: See USER_MANUAL.md and API_REFERENCE.md