# 📁 GitHub Repository Management Tab

The GitHub tab allows you to configure which GitHub repositories should be cloned and indexed for RAG (Retrieval Augmented Generation) processing.

## Overview

This tab provides a JSON-based configuration interface for managing GitHub repositories. You can edit the configuration directly in the JSON editor or use the template button for a quick start.

---

## GUI Design

### Layout Structure

The GitHub tab uses a **responsive, compact design** that adapts to screen width while maintaining optimal spacing and readability.

```
┌─────────────────────────────────────────────────────────────────┐
│  📁 GitHub Repository Management                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Edit repository configuration using JSON                       │
│  format. 💡 Tips: Click to edit • Ctrl+Enter to format          │
│                                                                 │
├──────────────────────────────┬─────────────────────────────────┤
│                              ║                                  │
│  Repository Configuration    ║  [📄]   Load Template           │
│  (JSON)                      ║     ─────────────────────       │
│  ┌────────────────────────────║                                 │
│  │ {                          ║  [🔍] Add SigmaHQ Repos         │
│  │   "repositories": []       ║     ────────────────────       │
│  │     {...}, ...             ║  [📂] Load Configuration        │
│  │   ]                        ║     ─────────────────────       │
│  │ }                          ║                                 │
│  └────────────────────────────║  [✅ Validate JSON]            │
│                              ║     ────────────────────        │
│                              ║  [💾 Save Configuration]        │
│                              ║     ─────────────────────       │
│                              ║  [🔄 Update All Repos]          │
│                              ║                                  │
├──────────────────────────────┴─────────────────────────────────┤
│  Status: Ready - Edit the JSON above...                        │
└─────────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
gr.Blocks()
└── gr.Column(variant="compact")
    ├── gr.Markdown("### 📁 GitHub Repository Management")
    ├── gr.Markdown("Edit repository configuration... 💡 Tips...")
    │
    ├── gr.Row(equal_height=False)  # Main layout row
    │   ├── gr.Column(scale=2, min_width=500)  # Left: JSON editor
    │   └── gr.Column(scale=1, min_width=160)  # Right: Buttons column
    │       ├── gr.Button("📄 Load Template", variant="secondary")
    │       ├── gr.Button("🔍 Add SigmaHQ Repos", variant="secondary")
    │       ├── gr.Button("📂 Load Configuration", variant="secondary")
    │       ├── gr.Button("✅ Validate JSON", variant="primary")
    │       ├── gr.Button("💾 Save Configuration", variant="primary")
    │       └── gr.Button("🔄 Update All Repos", variant="secondary")
    │
    └── gr.Textbox(label="", lines=2, container=False)  # Validation status (no border)
```

### CSS Styling Summary

| Selector | Property | Value | Purpose |
|----------|----------|-------|---------|
| `gr.Row(equal_height=False)` | Prevents vertical scrollbar on empty rows | Compact layout |
| `gr.Column(scale=2, min_width=500)` | Editor minimum width | 500px for comfortable editing |
| `gr.Column(scale=1, min_width=160)` | Button column width | Fits full button text |
| `gr.Textbox(lines=2, container=False)` | No border/padding | Clean status display |

---

## Dynamic Editor Behavior

The **Repository Configuration (JSON)** editor features:
- **Syntax highlighting** for JSON formatting with colored keywords, strings, numbers
- **Interactive editing** - click anywhere in the editor to modify values directly
- **Keyboard shortcuts**: `Ctrl+Enter` formats JSON on demand
- **Dynamic height** (`lines=12`) - expands based on content
- **Scroll within editor** when JSON exceeds 12 lines
- **Compact font**: 13px, line-height 1.45 for efficient workflow

### Keyboard Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Click` | Focus editor | Begin editing directly |
| `Ctrl+Enter` | Format JSON | Pretty-print the entire JSON structure |
| `Ctrl+A` | Select all | Highlight everything for copy/paste replacement |
| `Ctrl+C` / `Ctrl+V` | Copy/Paste | Standard clipboard operations |

---

## Action Buttons

### Left Column (JSON Editor)

**📄 Load Template**
- Resets editor to default template with example configuration
- Provides a clean starting point for new configurations
- Variant: secondary (gray)

**🔍 Add SigmaHQ Repos** *(NEW)*
- Fetches latest repositories from the SigmaHQ GitHub organization via API
- Adds missing repos to your configuration as disabled entries
- Automatically sets `enabled: false` so you can review before enabling
- Useful for discovering new docs, SDKs, or related projects
- **Important**: Changes are NOT auto-saved - you must click "💾 Save Configuration" to persist

### Right Column (Buttons)

| Button | Purpose | Visual State | Position |
|--------|---------|--------------|----------|
| 📄 Load Template | Load example config | Secondary (gray) | Top |
| 🔍 Add SigmaHQ Repos | Discover SigmaHQ repos | Secondary (gray) | New, below template |
| 📂 Load Configuration | Load saved config from disk | Secondary (gray) | Below SigmaHQ button |
| ✅ Validate JSON | Check syntax and structure | Primary (blue) | Top of button cluster |
| 💾 Save Configuration | Persist changes to `data/config.json` | Primary (blue) | Center of cluster |
| 🔄 Update All Repos | Clone and index enabled repositories | Secondary (gray) | Bottom |

### Button Layout Pattern

```
┌───────────────────────┐  ┌──────────────┐
│ 📄 Load Template       │  │              │
├───────────────────────┤  ├──────────────┤
│ 🔍 Add SigmaHQ Repos  │  │              │
├───────────────────────┤  ├──────────────┤
│ 📂 Load Config        │  │              │
├───────────────────────┤  ├──────────────┤
│ ✅ Validate JSON      │  │              │
├───────────────────────┤  ├──────────────┤
│ 💾 Save Config        │  │              │
├───────────────────────┤  ├──────────────┤
│ 🔄 Update All Repos   │  │              │
└───────────────────────┘  └──────────────┘
```

---

## Configuration Structure

The configuration file (`data/config.json`) uses a **flat structure** where `repositories` is at the root level:

### Complete Configuration Example

```json
{
  "network": {
    "ip": "127.0.0.1",
    "port": 8001,
    "auto_reload": false
  },
  
  "repositories": [
    {
      "url": "https://github.com/frack113/sigmahqrag.git",
      "branch": "main",
      "enabled": true,
      "file_extensions": ["py", "md"],
      "description": "SigmaHQ RAG main repository"
    },
    {
      "url": "https://github.com/frack113/sigmahq-docs.git",
      "branch": "main",
      "enabled": true,
      "file_extensions": ["md"],
      "description": "SigmaHQ documentation"
    }
  ],
  
  "llm": {
    "model": "qwen/qwen3.5-9b",
    "base_url": "http://127.0.0.1:1234/v1",
    "temperature": 0.7,
    "max_tokens": 5000
  },
  
  "ui_css": {
    "theme": "soft",
    "title": "SigmaHQ RAG"
  }
}
```

### Repository Object Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | ✅ | - | Full GitHub URL with `.git` suffix (e.g., `https://github.com/user/repo.git`) |
| `branch` | string | ✅ | - | Branch name to clone (e.g., `main`, `master`, `develop`, `dev`) |
| `enabled` | boolean | ⚠️ | `true` | Whether the repo should be cloned/indexed |
| `file_extensions` | array | ⚠️ | Common formats | List of extensions to index (case-insensitive) |
| `description` | string | ❌ | - | Human-readable description for reference |

### Supported File Extensions

| Category | Extensions |
|----------|------------|
| Python code | `.py`, `.pyi` |
| JavaScript/TypeScript | `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs` |
| Documentation | `.md`, `.txt`, `.rst`, `.docx` |
| Web files | `.html`, `.htm`, `.css`, `.scss` |
| Data config | `.json`, `.yaml`, `.yml`, `.xml` |

---

## Usage Workflow

### Quick Start (Recommended for Beginners)

1. **Click "📄 Load Template"** 
   - Gets a working example configuration
   
2. **Edit the JSON** 
   - Modify URLs, branches, and file extensions as needed
   - Use `Ctrl+Enter` to format if needed
   
3. **Click "✅ Validate JSON"** 
   - Ensures syntax is correct before saving
   
4. **Click "💾 Save Configuration"** 
   - Persists changes to `data/config.json`
   
5. **Click "🔄 Update All Repos"** 
   - Clones and indexes all enabled repositories

### Advanced Workflow (Using Add SigmaHQ)

1. **Click "📂 Load Configuration"**
   - Restores your last saved configuration
   
2. **Add SigmaHQ Repositories** *(NEW)*
   - Click **"🔍 Add SigmaHQ Repos"** to automatically discover available repos
   - The JSON editor updates immediately with new repo entries
   - Status message shows: `✅ Added X SigmaHQ repositories (disabled)`
   - New repos are added as `enabled: false` for review
   
3. **Review and Select**
   - Enable only the repos you want by changing `"enabled": true`
   
4. **Continue with validation and save**
   - Click "✅ Validate JSON" to check syntax
   - Click "💾 Save Configuration" to persist changes

---

## Status Messages Guide

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ Valid configuration: 2 total, 2 enabled, 0 disabled | Config is ready to use | You can save or update |
| ❌ JSON syntax error on line 3, column 15 | Invalid JSON format | Fix syntax before saving |
| ❌ Missing 'repositories' key | No repositories section | Add repositories array |
| ❌ Repository 2: Branch is required | Missing branch field | Add branch to repository |
| ✅ Configuration saved successfully | Changes persisted | Ready to update repositories |
| ⚠️ No enabled repositories found | All repos disabled or empty | Enable at least one repo |
| ✅ Added 5 SigmaHQ repositories (disabled) | Auto-discovered new repos | Review and enable desired ones |

### Add SigmaHQ Status Messages

When clicking **"🔍 Add SigmaHQ Repos"**, you may see:

| Message | Meaning | Next Step |
|---------|---------|-----------|
| ✅ Added X repos (disabled) | Successfully added repos | Click "💾 Save Configuration" to persist |
| ⚠️ Could not fetch... (network) | Network/API issue | Check internet connection |
| ℹ️ No new repos... | All repos already in config | Nothing to do, you can skip |

---

## Common Tasks

### Add a New Repository
1. **Option A**: Manually edit JSON
   ```json
   {
     "url": "https://github.com/username/repo.git",
     "branch": "main",
     "enabled": true,
     "file_extensions": ["py", "md"],
     "description": "My project repository"
   }
   ```

2. **Option B**: Use Add SigmaHQ button (for SigmaHQ repos)
   - Click **"🔍 Add SigmaHQ Repos"**
   - New repos appear in JSON editor immediately
   - Enable desired ones and save

### Disable a Repository
- Change `"enabled": true` to `"enabled": false` in the JSON
- Or click **"📂 Load Configuration"** and manually edit the field

### Update Only One Repository
1. Use **Ctrl+Enter** to format the JSON (helps spot changes)
2. Edit only the desired repository object
3. Validate and save as usual

### Format JSON Automatically
- Press `Ctrl+Enter` while in the editor
- Automatically pretty-prints with indentation

---

## Error Handling & Troubleshooting

### Configuration Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "❌ JSON syntax error on line X, column Y" | Missing comma, quote, bracket | Use a JSON validator or Ctrl+Enter to format |
| "❌ Validation errors: Repository 1: Branch is required" | Missing branch field | Add `"branch": "main"` to repository |
| "❌ Cannot save: repositories must be a list" | Wrong type | Ensure `repositories` is `[...]` not `{...}` |

### Update Errors

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Failed to clone repository" | Invalid URL or network issue | Check GitHub URL (must include `.git` suffix) |
| "Branch 'X' not found" | Branch name is incorrect | Use a valid branch from the repo |
| "Update failed: 503 Service Unavailable" | GitHub rate limit / network | Wait and retry, or check internet connection |

### General Troubleshooting

**Issue**: Buttons not responding
- Ensure application is still running (check for console output)
- Try clicking **"📂 Load Configuration"** first to verify UI works
- Refresh the tab if needed

**Issue**: Can't see full configuration
- Editor scrolls internally - use scrollbars in the editor window
- Use **Ctrl+Enter** to format and make structure clearer
- Status area at bottom shows validation summary

**Issue**: Updates seem stuck
- The "Update All Repos" button clones first, then indexes
- Check **"📋 Logs"** tab for real-time progress details
- Large repositories may take several minutes

---

## Best Practices

1. **Always validate before saving** 
   - Click **✅ Validate JSON** to catch syntax errors early
   
2. **Test with one repo first** 
   - Start by enabling a single small repository to verify workflow
   
3. **Use descriptive names in descriptions**
   - Helps identify repositories later when managing many repos
   
4. **Keep file extensions relevant**
   - Only index file types you actually need
   - Too many extensions = slower indexing, less focused results
   
5. **Enable repos selectively**
   - Use `"enabled": false` for test/temporary repositories
   - Add SigmaHQ repos in disabled state for review
   
6. **Regular maintenance**
   - Periodically run **"🔍 Add SigmaHQ Repos"** to keep up with new releases
   
7. **Backup your config**
   - The file `data/config.json` contains your complete configuration
   - Commit it to version control if appropriate

---

## Related Documentation

- [⚙️ CONFIG TAB](./tab_config.md) - Server and LLM settings
- [💬 CHAT TAB](./tab_chat.md) - Using the RAG chat interface
- [📊 DATA TAB](./tab_data.md) - Knowledge base management
- [USER MANUAL](./USER_MANUAL.md) - Complete application guide