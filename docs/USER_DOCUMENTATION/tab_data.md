# 📊 Data Management Tab

The Data tab allows you to manage the knowledge base used by the RAG system.

## Overview

This tab provides tools to update and manage your knowledge base. You can:
- Update indexed repositories from GitHub
- View real-time statistics about your knowledge base
- Reset the database to clear all indexed files and start from zero
- Monitor the indexing progress

---

## GUI Design

### Layout Structure

The Data tab uses a centered layout with buttons at the top and statistics below.

```
┌───────────────────────────────────────────────────────────────┐
│  ### Database Statistics 📊                                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │Update DB     │    │ Refresh      │    │ Reset        │   │
│  │              │    │ Statistics   │    │ Database     │   │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ {}                                                      │ │
│  │   (JSON display of statistics - updated on refresh)      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  Progress: Ready                                              │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Layout Order (top to bottom):**
1. **Database Statistics Header** - Section title
2. **Action Buttons Row** - Three buttons for main operations
3. **Statistics Display** - JSON output showing knowledge base stats
4. **Progress Status** - Text box showing current operation status

### Component Hierarchy

```
gr.Blocks(theme=gr.themes.Soft())
└── gr.Column(elem_classes="data-container")
    │
    ├── Header: "### Database Statistics 📊"
    │
    ├── self.stats_display = gr.JSON(
    │       label="Database Statistics", 
    │       value={})
    │
    ├── self.progress_text = gr.Textbox(
    │       label="Progress", 
    │       interactive=False, 
    │       value="Ready")
    │
    └── Action Buttons Row: gr.Row()
        │
        ├── self.update_btn = gr.Button("Update Database", variant="primary")
        ├── self.refresh_btn = gr.Button("Refresh Statistics")
        └── self.reset_btn = gr.Button("Reset Database")

└── All events use queue=True for async operations
```

### Component Specifications

#### Statistics Display (`self.stats_display`)
| Property | Value | Purpose |
|----------|-------|---------|
| `type` | JSON | Displays statistics as formatted JSON |
| `label` | "Database Statistics" | Clear header for the display |
| `value` | `{}` | Empty object initially |
| `interactive` | False | Read-only mode |

#### Progress Text (`self.progress_text`)
| Property | Value |
|----------|-------|
| `label` | "Progress" |
| `interactive` | False | Read-only status display |
| `value` | "Ready" | Initial state (changes during operations) |

#### Action Buttons (`gr.Row`)
Three equal-width buttons for the main data operations.

| Button Name | Display Text | Variant | Description |
|-------------|--------------|---------|-------------|
| `self.update_btn` | Update Database | primary | Main action - refreshes entire knowledge base from GitHub repos |
| `self.refresh_btn` | Refresh Statistics | secondary | Updates statistics display without re-indexing |
| `self.reset_btn` | Reset Database | secondary | Clears all indexed files and starts from zero |

---

## Operations Overview

### Update Database (Primary Action)
The main operation that refreshes your entire knowledge base.

**What it does:**
1. Loads GitHub repository configuration
2. Identifies enabled repositories
3. Clones/updates repository content in `data/github/`
4. Indexes documents for RAG

**Progress Messages:**
```
1. "Loading configuration..."     → Progress: "Loading configuration..."
2. "Updating X repositories..."    → Progress: "Updating X repositories..."
3. "Indexing repository content..." → Progress: "Indexing repository content..."
4. "✅ Knowledge base updated!"    → Stats updated with new values!
```

**Important:** Statistics are updated **during the update process**. As each step completes, the statistics display is refreshed to reflect current state. This allows you to monitor the indexing progress in real-time.

### Refresh Statistics

Fetches current statistics without re-indexing.

**Effect:**
- Fetches current context statistics from `data/github/`
- Updates `stats_display` JSON component
- Shows: "Data refreshed!" + new stats

### Reset Database

Completely clears the knowledge base by removing all indexed files and restarting from zero. This is useful when you want to start fresh or remove corrupted data.

**What it does:**
1. Deletes all contents of `data/github/` directory
2. Clears Chroma vector database in `data/chroma_db/`
3. Updates statistics to empty state

**Warning**: This action cannot be undone! All indexed documents will be permanently removed until you run "Update Database" again.

**Effect:**
```python
# Triggers full reset of database
yield "Database reset! Start by running Update Database.", {}
```

---

## Statistics Display Structure

The `stats_display` JSON component shows the following structure (from actual implementation):

```json
{
  "count": 150,
  "size_mb": 12.5,
  "embedding_model": "all-MiniLM-L6-v2",
  "default_chunk_size": 1000,
  "default_chunk_overlap": 200
}
```

| Field | Type | Description |
|-------|------|-------------|
| `count` | int | Total number of indexed files in `data/github/` directory |
| `size_mb` | float | Total size of indexed files in megabytes |
| `embedding_model` | string | Name of the embedding model used (currently: all-MiniLM-L6-v2) |
| `default_chunk_size` | int | Default chunk size for document processing |
| `default_chunk_overlap` | int | Default overlap between chunks in characters |

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

The update operation yields progress messages to keep the user informed.

| State | Message | Status |
|-------|---------|--------|
| Idle | "Ready" | No operation in progress |
| Config Loading | "Loading configuration..." | Initializing |
| Empty Config | "No repositories configured" | Warning |
| No Enabled | "No enabled repositories found" | Warning |
| Updating | "Updating X repositories..." (X = count) | In progress |
| Indexing | "Indexing repository content..." | Processing |
| Success | "✅ Knowledge base updated!" | Complete |
| Success (no files) | "No repositories were indexed" | Complete |
| Failed | "Error: {error}" | Error |

---

## Reset Database Progress Tracking

| State | Message | Status |
|-------|---------|--------|
| Starting | "Resetting database..." | In progress |
| Deleting Files | "Deleting indexed files..." | In progress |
| Clearing DB | "Clearing vector database..." | In progress |
| Success | "Database reset! Start by running Update Database." | Complete |

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No repositories configured | Empty configuration | Add repositories via GitHub tab |
| No enabled repositories | All repos disabled | Enable at least one repository |
| Clone failed | Network/GitHub issue | Check connection, retry update |
| Index returned false | Service unavailable | Files exist but weren't processed |
| General exception | Application error | Check logs in `data/logs/` directory |

---

## Use Cases

### Daily Maintenance
- **Morning**: Click "Update Database" to ensure latest code/docs are indexed
- **Monitor**: Check statistics to see knowledge base growth

### Troubleshooting
- **Missing content**: Update Database and wait for completion
- **No documents counted**: Check `data/github/` directory has cloned repos
- **Corrupted database**: Reset Database and re-run Update Database

### Performance Optimization
1. **After major commits**: Run Update Database to index changes
2. **Regular check**: Refresh Stats to see current state
3. **If app shows errors**: Reset Database to clear potential corruption

---

## Best Practices

1. **Update after significant changes** - Index new code/docs promptly
2. **Check stats regularly** - Monitor knowledge base growth
3. **Use Reset Database carefully** - Only when you need a clean slate
4. **After reset, run Update Database** - Re-populate your knowledge base
5. **Review enabled repositories** - Ensure all sources are up-to-date

---

## Related Documentation

- [📁 GitHub Tab](./tab_github.md) - Configure repositories to index
- [💬 Chat Tab](./tab_chat.md) - Use the knowledge base in conversations
- [📋 USER MANUAL](./USER_MANUAL.md) - Complete application overview