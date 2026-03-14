# 📊 Data Management Tab

The Data tab allows you to manage the knowledge base used by the RAG system.

## Overview

This tab provides tools to update and refresh your knowledge base. You can:
- Update indexed repositories from GitHub
- View real-time statistics about your knowledge base
- Clear the context cache to free resources
- Monitor the indexing progress

---

## GUI Design

### Layout Structure

The Data tab uses a centered layout with prominent action buttons.

```
┌───────────────────────────────────────────────────────────────┐
│  ### Database Statistics 📊                                   │
├───────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ {}                                                       │ │
│  │   (JSON display of statistics)                           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Progress: Ready                                              │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │Update DB     │    │  Refresh     │    │  Clear       │   │
│  │              │    │  Stats       │    │  Context     │   │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
gr.Blocks(theme=gr.themes.Soft())
└── gr.Column(elem_classes="data-container")
    ├── gr.Markdown("### Database Statistics 📊")
    │
    ├── self.stats_display = gr.JSON(value={})
    │   └── Label: "Database Statistics"
    │
    ├── self.progress_text = gr.Textbox(
    │       label="Progress", 
    │       interactive=False, 
    │       value="Ready")
    │
    └── gr.Row() # Action buttons
        ├── self.update_btn = gr.Button("Update Database", variant="primary")
        ├── self.refresh_btn = gr.Button("Refresh Stats")
        └── self.clear_btn = gr.Button("Clear Context")

└── Events: All buttons use queue=True for async operations
```

### Component Specifications

#### Statistics Display (`self.stats_display`)
| Property | Value | Purpose |
|----------|-------|---------|
| `type` | JSON | Displays statistics as formatted JSON |
| `label` | "Database Statistics" | Clear header for the display |
| `value` | {} | Empty object initially |
| `interactive` | True/False | Can be read-only mode |

#### Progress Text (`self.progress_text`)
| Property | Value |
|----------|-------|
| `label` | "Progress" |
| `interactive` | False | Read-only status display |
| `value` | "Ready" | Initial state |

#### Action Buttons (`gr.Row`)
Three equal-width buttons for the main data operations.

| Button | Variant | Description |
|--------|---------|-------------|
| Update Database | primary | Main action - refreshes entire knowledge base |
| Refresh Stats | secondary | Updates statistics display only |
| Clear Context | secondary | Clears RAG context cache |

---

## Operations Overview

### Update Database (Primary Action)
The main operation that refreshes your entire knowledge base.

**What it does:**
1. Loads GitHub repository configuration
2. Identifies enabled repositories
3. Clones/updates repository content
4. Indexes documents for RAG

**Progress Messages:**
```
1. "Loading configuration..."
2. "Updating X repositories..."
3. "Indexing repository content..."
4. "✅ Knowledge base updated! Indexed Y documents from Z repositories."
```

### Refresh Stats
Updates the statistics display without re-indexing.

**Effect:**
- Fetches current context statistics
- Updates `stats_display` JSON component
- Shows: "Data refreshed!" + new stats

### Clear Context
Removes the RAG context cache to free memory.

**Effect:**
```python
if success:
    # Re-fetch stats after clear
    yield "Context cleared!", updated_stats
else:
    yield "Failed to clear context", {}
```

---

## Statistics Display Structure

The `stats_display` JSON component shows the following structure:

```json
{
  "count": 150,
  "total_tokens": 45000,
  "repos_indexed": 2,
  "documents_processed": 150,
  "last_update": "2026-03-14T15:47:39Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `count` | int | Total number of indexed documents |
| `total_tokens` | int | Total tokens in the knowledge base |
| `repos_indexed` | int | Number of repositories currently indexed |
| `documents_processed` | int | Same as count, for clarity |
| `last_update` | string | ISO timestamp of last index update |

---

## Update Workflow Details

### Step 1: Configuration Load
```python
repo_config = self.data_service.get_repo_config()
if not repo_config["repositories"]:
    yield "No repositories configured"
    return
```

### Step 2: Identify Enabled Repositories
```python
enabled_repos = [
    repo for repo in repo_config["repositories"] 
    if repo["enabled"]
]
if not enabled_repos:
    yield "No enabled repositories found"
    return
```

### Step 3: Clone/Update Repositories
```python
clone_result = self.data_service.clone_enabled_repositories(repo_config)
```

### Step 4: Index Repository Content
```python
index_result = self.data_service.index_enabled_repositories(repo_config)
```

### Step 5: Update Statistics
```python
updated_stats = self.data_service.get_context_stats()
yield success_msg, updated_stats
```

---

## Progress Tracking

The update operation yields progress messages to keep the user informed:

| State | Message | Status |
|-------|---------|--------|
| Idle | "Ready" | No operation in progress |
| Config Loading | "Loading configuration..." | Initializing |
| Empty Config | "No repositories configured" | Warning |
| No Enabled | "No enabled repositories found" | Warning |
| Updating | "Updating X repositories..." | In progress |
| Indexing | "Indexing repository content..." | Processing |
| Success | "✅ Knowledge base updated!" | Complete |
| Failed | "Error: {error}" | Error |

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No repositories configured | Empty configuration | Add repositories via GitHub tab |
| No enabled repositories | All repos disabled | Enable at least one repository |
| Clone failed | Network/GitHub issue | Check connection, retry update |
| Index failed | Service unavailable | Check LLM/embedding service status |

---

## Use Cases

### Daily Maintenance
- **Morning**: Click "Update Database" to ensure latest code/docs are indexed
- **Monitor**: Check statistics to see knowledge base growth

### Troubleshooting
- **Slow responses**: Clear Context to free memory, then refresh stats
- **Missing content**: Update Database and wait for completion

### Performance Optimization
1. **After major commits**: Run Update Database to index changes
2. **If app slows down**: Use Clear Context to reclaim memory
3. **Regular check**: Refresh Stats to see current state

---

## Best Practices

1. **Update after significant changes** - Index new code/docs promptly
2. **Check stats regularly** - Monitor knowledge base growth
3. **Clear context periodically** - Prevent memory buildup
4. **Review enabled repositories** - Ensure all sources are up-to-date

---

## Related Documentation

- [📁 GitHub Tab](./tab_github.md) - Configure repositories to index
- [💬 Chat Tab](./tab_chat.md) - Use the knowledge base in conversations
- [📋 USER MANUAL](./USER_MANUAL.md) - Complete application overview