# ⚙️ Server Configuration Tab

The Config tab allows you to manage application settings through JSON editing.

## Overview

This tab provides a JSON-based configuration interface for managing server and application settings. You can:
- View and edit the current configuration
- Save changes persistently
- Reset to default settings
- Validate JSON before saving

---

## GUI Design

### Layout Structure

The Config tab uses a centered layout with a large editable text area.

```
┌───────────────────────────────────────────────────────────────┐
│  ### Server Configuration                                     │
├───────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ {                                                        │ │
│  │   "network": {                                           │ │
│  │     "ip": "127.0.0.1",                                   │ │
│  │     "port": 8000                                         │ │
│  │   },                                                     │ │
│  │   ... (full configuration JSON)                          │ │
│  │                                                          │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Status: Ready                                                 │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │📂 Load Config│    │💾 Save Config│    │↻ Reset to    │   │
│  ├──────────────┤    ├──────────────┤    │  Default     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
gr.Blocks(theme=gr.themes.Soft())
└── gr.Column(elem_classes="config-container")
    ├── gr.Markdown("### ⚙️ Server Configuration")
    │
    ├── self.config_display = gr.Textbox(
    │       value="",
    │       label="Current Configuration",
    │       lines=12,
    │       interactive=True,
    │       max_lines=15)
    │
    ├── gr.Row() # Action buttons
    │   ├── self.load_btn = gr.Button("📂 Load Config")
    │   ├── self.save_btn = gr.Button("💾 Save Config")
    │   └── self.reset_btn = gr.Button("↻ Reset to Default")
    │
    └── self.status_text = gr.Textbox(
            label="Status", 
            interactive=False, 
            value="Ready")

└── Events: All buttons use queue=True for async operations
```

### Component Specifications

#### Configuration Display (`self.config_display`)
| Property | Value | Purpose |
|----------|-------|---------|
| `label` | "Current Configuration" | Section header |
| `lines` | 12 | Initial height |
| `interactive` | True | Editable JSON editor |
| `max_lines` | 15 | Wraps after 15 lines |

The textbox allows direct editing of the configuration as a formatted JSON object.

#### Status Text (`self.status_text`)
| Property | Value |
|----------|-------|
| `label` | "Status" |
| `interactive` | False | Read-only status display |
| `value` | "Ready" | Initial state |

#### Action Buttons (`gr.Row`)
Three buttons for configuration management.

| Button | Description |
|--------|-------------|
| Load Config | Loads current configuration from disk |
| Save Config | Saves edited configuration to disk |
| Reset to Default | Resets to factory default settings |

---

## Configuration Structure

The application configuration consists of these main sections:

```json
{
  "network": {
    "ip": "127.0.0.1",
    "port": 8000,
    "auto_reload": true
  },
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "base_url": "http://127.0.0.1:1234",
    "temperature": 0.7,
    "max_tokens": 5000
  },
  "repositories": [
    {
      "url": "https://github.com/user/repo.git",
      "branch": "main",
      "enabled": true,
      "file_extensions": ["py", "js"],
      "description": "Example repository"
    }
  ],
  "ui_css": {
    "theme": "soft",
    "title": "SigmaHQ RAG"
  }
}
```

### Configuration Sections

#### Network (`network`)
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ip` | string | ✅ | - | Server IP address |
| `port` | int | ✅ | - | Server port number |
| `auto_reload` | bool | ⚠️ | true | Auto-reload on file changes |

#### LLM (`llm`)
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model` | string | ✅ | - | Model identifier (e.g., "qwen/qwen3.5-9b") |
| `base_url` | string | ✅ | - | Model server URL |
| `temperature` | float | ⚠️ | 0.7 | LLM temperature (creativity) |
| `max_tokens` | int | ⚠️ | 5000 | Maximum output tokens |

#### Repositories (`repositories`)
Array of repository objects with:
- `url`: GitHub URL with `.git` suffix
- `branch`: Branch name to clone
- `enabled`: Boolean flag for active status
- `file_extensions`: Array of file extensions to index
- `description`: Optional description text

#### UI CSS (`ui_css`)
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `theme` | string | ✅ | soft | Gradio theme name |
| `title` | string | ✅ | "SigmaHQ RAG" | App title text |

---

## Operations Overview

### Load Config (Primary Action)
Loads the current configuration from `data/config.json`.

**Process:**
```python
config_mgr = create_config_manager()
config = config_mgr.get_config_for_ui()
config_json = json.dumps(config, indent=2)
return config_json, "✅ Configuration loaded"
```

**Display:** The full JSON configuration is shown in the editable text area.

### Save Config (Primary Action)
Saves the edited configuration back to `data/config.json`.

**Process:**
```python
# 1. Parse and validate JSON
parsed = self._parse_json(json_string)

if parsed is None:
    return "❌ Invalid JSON format"

# 2. Update via config manager
result = self.config_service.config_manager.update_config(parsed)

if result:
    return "✅ Configuration saved successfully"
else:
    return "❌ Failed to save configuration"
```

### Reset to Default
Restores factory default settings.

**Default Configuration:**
```json
{
  "network": {
    "ip": "127.0.0.1",
    "port": 8000
  },
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "temperature": 0.7,
    "max_tokens": 5000,
    "base_url": "http://127.0.0.1:1234"
  },
  "repositories": [],
  "ui_css": {
    "theme": "soft",
    "title": "SigmaHQ RAG"
  }
}
```

---

## Validation Rules

### Required Fields Check
The validation process ensures these fields are present:

```python
def _parse_json(self, json_string: str) -> dict | None:
    # Validate required fields based on config structure
    if "network" not in parsed:
        return {"error": "Missing 'network' section"}
    
    for field in ["ip", "port"]:
        if field not in network_config:
            return {"error": f"Missing '{field}' in network config"}
    
    if "llm" not in parsed:
        return {"error": "Missing 'llm' section"}
    
    for field in ["model", "base_url", "temperature", "max_tokens"]:
        if field not in llm_config:
            return {"error": f"Missing '{field}' in llm config"}
```

### Common Validation Errors
| Error | Cause | Solution |
|-------|-------|----------|
| Missing 'network' section | Section not present | Add network with ip and port |
| Missing 'llm' section | Section not present | Add llm with model and base_url |
| Invalid JSON format | Syntax error in text area | Fix brackets, quotes, commas |
| Empty configuration | Text cleared | Load config first before editing |

---

## Workflow Examples

### Editing Network Settings
```python
# 1. Click "📂 Load Config" to see current settings
# 2. Edit the "network" section in text area:
    "ip": "0.0.0.0",      # Change to listen on all interfaces
    "port": 8080          # Change port number

# 3. Click "💾 Save Config" to persist changes
# 4. Restart application for settings to take effect
```

### Adding a Repository
```python
# Load config and add to repositories array:
{
  "repositories": [
    {
      "url": "https://github.com/frack113/sigmahqrag.git",
      "branch": "main",
      "enabled": true,
      "file_extensions": ["py", "md"]
    }
  ]
}

# Save with "💾 Save Config" button
```

### Changing LLM Model
```python
{
  "llm": {
    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "base_url": "http://localhost:1234/v1",
    "temperature": 0.5,
    "max_tokens": 2000
  }
}

# Save and restart app
```

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid JSON | Syntax errors in text area | Use Load Config to restore valid format |
| File permission denied | Can't write to config file | Check folder permissions |
| Missing required field | Validation failed | Add missing fields per validation rules |
| Network unreachable | Model server not running | Start the model server before using RAG |

---

## Best Practices

1. **Backup before editing** - Load current config, copy as backup
2. **Validate before saving** - Check JSON syntax carefully
3. **Restart after changes** - Some settings require app restart
4. **Keep a local copy** - Version control your config if possible
5. **Test one change at a time** - Don't make multiple edits simultaneously

---

## Related Documentation

- [📁 GitHub Tab](./tab_github.md) - Configure repository indexing
- [💬 Chat Tab](./tab_chat.md) - RAG configuration options
- [📋 USER MANUAL](./USER_MANUAL.md) - Complete application overview