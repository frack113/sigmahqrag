# SigmaHQ RAG - Quick Start Production Guide

## Fast Track to Production

This guide provides the fastest path to get SigmaHQ RAG running in production.

## Prerequisites
- Linux server with Python 3.10+
- 4GB+ RAM
- 10GB+ disk space
- Internet connection

## 5-Minute Production Setup

### Step 1: Install and Setup (2 minutes)
```bash
# Clone repository
git clone <repository-url>
cd sigmahqrag

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install production dependencies
uv install --prod

# Setup production environment
uv run python main.py --production --setup-only
```

### Step 2: Configure (1 minute)
```bash
# Edit production configuration (optional)
nano data/config/production.json

# Set environment variables
export SIGMAHQ_ENV="production"
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

### Step 3: Start Application (1 minute)
```bash
# Start in production mode
uv run python main.py --production --host 0.0.0.0 --port 8000
```

### Step 4: Verify (1 minute)
```bash
# Check if running
curl http://localhost:8000/health

# Expected response: {"status": "healthy", ...}
```

## Production Deployment Commands

### Basic Production Start
```bash
# Start with default settings
uv run python main.py --production

# Start with custom host/port
uv run python main.py --production --host 0.0.0.0 --port 8000

# Setup only (no app start)
uv run python main.py --production --setup-only
```

### Systemd Service (Recommended)
```bash
# Create systemd service
sudo tee /etc/systemd/system/sigmahqrag.service > /dev/null <<EOF
[Unit]
Description=SigmaHQ RAG Application
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PYTHONPATH=$(pwd)
Environment=SIGMAHQ_ENV=production
ExecStart=$(which uv) run python main.py --production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sigmahqrag
sudo systemctl start sigmahqrag

# Check status
sudo systemctl status sigmahqrag
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t sigmahqrag:production .
docker run -d --name sigmahqrag -p 8000:8000 sigmahqrag:production
```

## Monitoring Commands

### Check System Health
```bash
# Get system health status
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
health = setup.get_system_health()
print(f'Status: {health[\"status\"]}')
print(f'CPU: {health[\"cpu\"][\"percent\"]}%')
print(f'Memory: {health[\"memory\"][\"percent\"]}%')
"
```

### View Logs
```bash
# View production logs
tail -f logs/production.log

# View deployment logs
tail -f logs/deployment.log
```

### Performance Monitoring
```bash
# Monitor resource usage
watch -n 5 "uv run python -c '
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
h = setup.get_system_health()
print(f\"CPU: {h[\"cpu\"][\"percent\"]}% | Memory: {h[\"memory\"][\"percent\"]}% | Disk: {h[\"disk\"][\"percent\"]}%\")
'"
```

## Troubleshooting

### Application Won't Start
```bash
# Check logs for errors
tail -n 50 logs/production.log

# Check port availability
netstat -tlnp | grep :8000

# Check Python path
echo $PYTHONPATH
```

### Port Already in Use
```bash
# Use different port
uv run python main.py --production --port 8001

# Or kill existing process
sudo kill -9 $(lsof -t -i:8000)
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $(whoami):$(whoami) data/ logs/
sudo chmod -R 755 data/ logs/
```

### LM Studio Issues
```bash
# Check LM Studio status
curl http://localhost:1234/v1/models

# Restart LM Studio
systemctl restart lm-studio
```

## Production Best Practices

### Security
```bash
# Use HTTPS (recommended)
# Configure firewall
sudo ufw allow 8000/tcp
sudo ufw enable

# Set up reverse proxy (nginx)
sudo apt install nginx
# Configure nginx for SSL termination
```

### Performance
```bash
# Monitor resource usage
htop

# Optimize configuration
# Edit data/config/production.json
{
  "workers": 2,
  "memory_limit_mb": 4096,
  "cpu_limit_percent": 90.0
}
```

### Backups
```bash
# Create configuration backup
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
setup.backup_configuration()
"

# Backup data directory
tar -czf backup_$(date +%Y%m%d).tar.gz data/
```

## Production Checklist

- [ ] Application starts successfully
- [ ] Health check returns healthy
- [ ] Logs show no errors
- [ ] Port is accessible
- [ ] LM Studio is running
- [ ] Database is accessible
- [ ] Firewall allows port 8000
- [ ] Systemd service is enabled (if using)
- [ ] Monitoring is configured
- [ ] Backups are scheduled

## Next Steps

1. **Configure HTTPS**: Set up SSL certificates
2. **Set up monitoring**: Configure alerting
3. **Optimize performance**: Tune configuration
4. **Security hardening**: Review security settings
5. **Load testing**: Test under load
6. **Documentation**: Update runbooks

## Support

- **Logs**: `logs/production.log`
- **Configuration**: `data/config/production.json`
- **Documentation**: `DEPLOYMENT_GUIDE.md`
- **Issues**: Check logs and run health checks

## Emergency Procedures

### Application Down
```bash
# Check service status
sudo systemctl status sigmahqrag

# Restart service
sudo systemctl restart sigmahqrag

# Check logs
sudo journalctl -u sigmahqrag -f
```

### Database Issues
```bash
# Check database health
uv run python -m src.infrastructure.database_setup --health

# Run maintenance
uv run python -m src.infrastructure.database_setup --maintenance
```

### High Resource Usage
```bash
# Check resource usage
uv run python -c "
from src.infrastructure.production_setup import ProductionSetup
setup = ProductionSetup()
print(setup.get_system_health())
"

# Restart if needed
sudo systemctl restart sigmahqrag
```

This quick start guide gets you to production in 5 minutes. For detailed configuration and advanced features, see the full [Deployment Guide](DEPLOYMENT_GUIDE.md).