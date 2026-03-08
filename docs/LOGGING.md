# Logging System Documentation

## Overview

The SigmaHQ RAG application now includes a robust logging system with automatic log rotation and a real-time log viewer interface.

## Features

### Log Rotation
- **Size-based rotation**: Logs are rotated when they reach 10MB (configurable)
- **Backup retention**: Keeps up to 5 rotated log files
- **Automatic cleanup**: Old rotated files are automatically managed
- **Zero downtime**: Rotation happens seamlessly without interrupting the application

### Log Viewer (Logs Page)
- **Real-time monitoring**: Live tail-like functionality showing new log entries as they occur
- **Filtering capabilities**: Filter logs by text content and log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Auto-scroll**: Automatically scrolls to the latest entries
- **Log management**: Clear logs, download log files, refresh view
- **Log information**: View current log file size, rotation status, and backup files

### Centralized Logging
- **Unified logger**: All application components use the same logging service
- **Structured format**: Consistent timestamp, logger name, level, and message format
- **Multiple outputs**: Logs go to both file and console
- **Configurable levels**: Adjust log verbosity as needed

## Usage

### Accessing the Logs Page
1. Start the application: `python main.py`
2. Navigate to the web interface: `http://localhost:8000`
3. Click the "Logs" button in the header navigation
4. The Logs page will display with filtering options and real-time monitoring

### Log Monitoring
- **Start monitoring**: Click "Start Monitoring" to begin real-time log viewing
- **Stop monitoring**: Click "Stop Monitoring" to pause real-time updates
- **Filter logs**: Use the filter input and log level dropdown to narrow down entries
- **Auto-scroll**: Toggle auto-scroll on/off based on preference

### Log Management
- **Clear logs**: Permanently delete all log entries (with confirmation)
- **Download logs**: Access the current log file for external analysis
- **Refresh**: Update the log display with any new entries

### Programmatic Usage

#### Getting a Logger
```python
from src.nicegui_app.models.logging_service import get_logger

# Get a logger instance
logger = get_logger(__name__)

# Use standard logging methods
logger.info("Information message")
logger.warning("Warning message") 
logger.error("Error message")
logger.debug("Debug message")
```

#### Accessing Log Information
```python
from src.nicegui_app.models.logging_service import logging_service

# Get recent log entries
recent_logs = logging_service.get_recent_logs(100)

# Get log file information
log_info = logging_service.get_log_file_info()
print(f"Current log size: {log_info['size_mb']} MB")

# Clear all logs
success = logging_service.clear_logs()
```

## Configuration

### Log Rotation Settings
The logging service can be configured with different rotation parameters:

```python
from src.nicegui_app.models.logging_service import LoggingService

# Custom configuration
logging_service = LoggingService(
    log_dir="custom_logs",      # Custom log directory
    max_bytes=50 * 1024 * 1024, # 50MB max file size
    backup_count=10             # Keep 10 backup files
)
```

### Log Level Control
```python
from src.nicegui_app.models.logging_service import logging_service

# Get current log level
current_level = logging_service.get_log_level()

# Set new log level
logging_service.set_log_level("DEBUG")  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Log File Locations

### Default Location
- **Log directory**: `./logs/`
- **Main log file**: `./logs/app.log`
- **Rotated files**: `./logs/app.log.1`, `./logs/app.log.2`, etc.

### Log Format
```
2026-03-08 13:45:30 - module_name - INFO - This is a log message
```

## Troubleshooting

### Common Issues

1. **Permission errors**: Ensure the application has write permissions to the logs directory
2. **Disk space**: Monitor disk usage as rotated logs consume space
3. **Log flooding**: Adjust log levels to reduce verbosity in production

### Log Analysis
- Use the filtering features to isolate specific issues
- Download logs for analysis with external tools
- Monitor log file sizes to prevent disk space issues

## Integration

The logging system is automatically integrated throughout the application:

- **Main application**: Logs startup, shutdown, and major events
- **Chat service**: Logs conversation management and document processing
- **Data service**: Logs database operations and repository indexing
- **LLM service**: Logs model interactions and API calls
- **RAG service**: Logs vector database operations and context management

All existing loggers have been updated to use the centralized logging service for consistent behavior and management.