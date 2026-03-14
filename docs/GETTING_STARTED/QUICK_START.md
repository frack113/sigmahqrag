# SigmaHQ RAG - Quick Start Guide

## Fast Track to Production

This guide provides the fastest path to get SigmaHQ RAG running.

## Prerequisites
- Linux server with Python 3.10+
- 2GB+ RAM
- 5GB+ disk space
- Internet connection

## 5-Minute Setup

### Step 1: Install and Setup (2 minutes)
```bash
# Clone repository
git clone <repository-url>
cd sigmahqrag

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv install --prod

# Start the application
uv run python main.py
```

### Step 2: Access Application
1. Open browser to `http://localhost:8000`
2. Test with a simple question
3. Add documents via Data tab

### Step 3: Verify
```bash
# Check if running
curl http://localhost:8000/health

# Expected response: Application is healthy
```

## Production Deployment (Systemd Service)

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
Environment="PYTHONPATH=$(pwd)"
ExecStart=$(which uv) run python main.py
Restart=always

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

## Configuration

Edit `data/config.json`:
```json
{
  "network": {
    "ip": "0.0.0.0",
    "port": 8000,
    "timeout": 30
  },
  "llm": {
    "base_url": "http://localhost:1234",
    "model": "qwen/qwen3.5-9b"
  }
}
```

## Troubleshooting

### Application Won't Start
```bash
# Check logs
tail -n 50 logs/*.log

# Check port
netstat -tlnp | grep :8000
```

### Port in Use
```bash
# Kill process or use different port
uv run python main.py --port 8001
```

## Next Steps
1. Configure LM Studio for LLM integration
2. Add documents via Data tab
3. Customize configuration in `data/config.json`
4. Set up monitoring and logging

## Support
- **Logs**: `logs/*.log`
- **Config**: `data/config.json`
- **Manuals**: See USER_MANUAL.md and DEPLOYMENT_GUIDE.md