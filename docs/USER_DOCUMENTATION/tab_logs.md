# 📋 Logs Viewer Tab

The Logs tab provides a viewer for monitoring application logs and system activities.

## Overview

This tab allows you to:
- View recent log entries from the application
- Refresh logs to get the latest entries
- Clear and backup old logs
- Monitor errors and warnings

---

## GUI Design

### Layout Structure

The Logs tab uses a simple vertical layout with a large text area for displaying logs.

```
┌───────────────────────────────────────────────────────────────┐
│  ### Logs Viewer 📋                                          │
├───────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                        │   │
│  │  No logs available. Click 'Refresh Logs' to update.    │   │
│  │                                                        │   │
│  │  Status: Ready                                        │   │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐                         │
│  │🔄 Refresh    │    │🗑️ Clear      │                         │
│  │Logs          │    │History       │                         │
│  ├──────────────┤    ├──────────────┤                         │
│  └──────────────┘    └──────────────┘                         │
└───────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
gr.Blocks(theme=gr.themes.Soft())
└── gr.Column(elem_classes="logs-container")
    ├── gr.Markdown("### Logs Viewer 📋")
    │
    ├── self.log_display = gr.Textbox(
    │       value=self.log_display_value,
    │       label="Logs",
    │       interactive=False,
    │       lines=20,
    │       max_lines=30)
    │
    ├── self.status_text = gr.Textbox(
    │       label="Status", 
    │       interactive=False, 
    │       value="Ready")
    │
    └── gr.Row() # Action buttons row
        ├── self.refresh_btn = gr.Button("🔄 Refresh Logs")
        └── self.clear_btn = gr.Button("🗑️ Clear History")

└── Events: All buttons use queue=True for async operations
```

### Component Specifications

#### Log Display (`self.log_display`)
| Property | Value | Purpose |
|----------|-------|---------|
| `label` | "Logs" | Section header |
| `interactive` | False | Read-only log display |
| `lines` | 20 | Initial height |
| `max_lines` | 30 | Wraps after 30 lines |
| `value` | "No logs available..." | Placeholder message |

The textbox supports **Markdown formatting**, allowing colored headers and code blocks.

#### Status Text (`self.status_text`)
| Property | Value |
|----------|-------|
| `label` | "Status" |
| `interactive` | False | Read-only status display |
| `value` | "Ready" | Initial state |

#### Action Buttons (`gr.Row`)
Two buttons for log management.

| Button | Description |
|--------|-------------|
| Refresh Logs | Updates and displays recent log entries |
| Clear History | Clears logs and backs them up to archive |

---

## Operations Overview

### Refresh Logs (Primary Action)
Loads the most recent log entries from disk.

**What it does:**
1. Scans the `logs/` directory for log files
2. Displays last 50 lines from each of the 3 most recent files
3. Shows file names as Markdown headers
4. Formats code blocks with syntax highlighting

**Output Format:**
```markdown
📄 Loaded 3 log file(s)

---

**app.log**
```
2026-03-14 15:49:15 INFO  Starting application...
2026-03-14 15:49:16 DEBUG Loading configuration...
2026-03-14 15:49:16 INFO  Configuration loaded successfully
... (up to 50 lines per file) ...
```

---

**2026-03-14 16:01:23 WARNING Connection timeout...**
```
```

### Clear History
Clears current logs and backs them up.

**Process:**
1. Creates backup directory: `logs_backup/YYYYMMDD_HHMMSS/`
2. Moves all log files to the backup directory
3. Returns "Logs cleared" status
4. Shows confirmation message

**Backup Location:**
```
logs_backup/YYYYMMDD_HHMMSS/
├── app.log
├── uv.log
└── ...
```

---

## Log File Structure

### Logs Directory
```
logs/
├── app.log          - Main application logs
├── uv.log           - Uvicorn/asyncio logs
└── other_logs*.log  - Various service logs
```

### Log Entry Format
```
{timestamp} {level} {message}
2026-03-14 15:49:15 INFO  Starting application...
2026-03-14 15:49:16 DEBUG Loading configuration from config.json
2026-03-14 15:49:17 WARNING Connection timeout after 30s
```

### Log Levels
| Level | Format | Description |
|-------|--------|-------------|
| INFO | `INFO` | Informational messages |
| DEBUG | `DEBUG` | Debug details (verbose) |
| WARNING | `WARNING` | Warnings about issues |
| ERROR | `ERROR` | Error messages |
| CRITICAL | `CRITICAL` | Critical system failures |

---

## Refresh Workflow

### Step 1: Scan Logs Directory
```python
logs_dir = Path("logs")
if logs_dir.exists():
    logfile_names = sorted(
        [f.name for f in logs_dir.glob("*.*")], 
        reverse=True
    )
```

### Step 2: Load Recent Entries (Per File)
```python
for filename in logfile_names[:3]:  # Limit to last 3 files
    filepath = logs_dir / filename
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        count = 0
        for line in reversed(f):  # Newest first
            if count < 50:  # Last 50 lines only
                logs.append(line.rstrip())
            count += 1
```

### Step 3: Format and Display
```python
log_text = "\n".join(logs)
return f"📄 Loaded {len(logfile_names)} log file(s)", log_text
```

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No logs found | Logs directory empty or missing | Application may not have started yet |
| Read error | File permissions issue | Check file permissions on logs/ folder |
| Encoding error | Non-UTF8 characters | Logs will use replacement character |

---

## Use Cases

### Troubleshooting Issues
1. **App won't start:** Refresh Logs to check for startup errors
2. **Slow performance:** Look for WARNING or ERROR entries
3. **Data sync issues:** Check logs for timeout messages

### Monitoring Activity
1. **After major changes:** Refresh Logs to see if changes were processed
2. **During updates:** Monitor for progress indicators
3. **For debugging:** Clear History then restart app fresh

### Log Cleanup
1. **Periodic cleanup:** Clear History removes old logs
2. **Backup created:** All logs are backed up before clearing
3. **Access backup:** Navigate to `logs_backup/` folder manually

---

## Backup Management

### Automatic Backup
Every time you clear logs, a timestamped backup is created:
```
logs_backup/20260314_164915/
├── app.log
├── uv.log
└── ...
```

### Manual Access to Backups
```python
backup_dir = Path("logs_backup") / backup_timestamp
# Navigate there manually or via file explorer
```

---

## Best Practices

1. **Refresh after errors** - Check logs immediately when issues occur
2. **Clear periodically** - Prevent disk space buildup (use Clear History)
3. **Monitor WARNING/ERROR** - Watch for recurring issues
4. **Keep backups** - Logs are automatically backed up before clearing

---

## Log Levels Explained

### INFO
Normal operational messages. Shows successful operations like:
- Application startup
- Configuration loaded
- Repository updated
- Files processed successfully

### WARNING
Indicates potential issues that may need attention:
- Connection timeouts
- Deprecated features
- Slow operations
- Fallback behavior triggered

### ERROR
Serious problems requiring investigation:
- Failed operations
- Data corruption detected
- Service unavailable
- Validation failures

### CRITICAL
Severe errors affecting system stability:
- Database connection lost
- Memory allocation failure
- Authentication failure
- Service crash imminent

---

## Related Documentation

- [📋 USER MANUAL](./USER_MANUAL.md) - Complete application overview
- [⚙️ API REFERENCE](./API_REFERENCE.md) - Technical API details