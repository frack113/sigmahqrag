# 📂 Files Management Tab

The Files tab provides file management capabilities for handling local files within the application.

## Overview

This tab allows you to:
- Upload files to be indexed or processed
- List directory contents from the `data/github` folder
- Download files from the repository storage
- Create new template files

---

## GUI Design

### Layout Structure

The Files tab uses a standard layout with upload area on top and action buttons in the middle.

```
┌───────────────────────────────────────────────────────────────┐
│  ### File Management 📁                                      │
├───────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │      [📎 Upload Files]                                  │ │
│  │                                                         │ │
│  │   (Drag & drop area for .py, .js, .ts, .html, etc.)     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Status: Ready                                                 │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │Upload Files  │    │List Directory│    │Download File │   │
│  ├──────────────┤    ├──────────────┤    ├──────────────┤   │
│  │ Create File   │    │              │    │              │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Results (5 lines, max 8):                                │ │
│  │                                                           │ │
│  │                                                           │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
gr.Blocks(theme=gr.themes.Soft())
└── gr.Column(elem_classes="file-container")
    ├── gr.Markdown("### File Management 📁")
    │
    ├── self.upload_area = gr.File(
    │       label="Upload Files",
    │       file_types=[".py", ".js", ".ts", "html", "css", 
    │                    ".json", ".txt"],
    │       type="binary")
    │
    ├── self.status_text = gr.Textbox(
    │       label="Status", 
    │       interactive=False, 
    │       value="Ready")
    │
    ├── gr.Row() # Action buttons row
    │   ├── self.upload_btn = gr.Button("Upload Files", variant="primary")
    │   ├── self.list_files_btn = gr.Button("List Directory")
    │   ├── self.download_btn = gr.Button("Download File")
    │   └── self.create_file_btn = gr.Button("Create File")
    │
    └── self.results_text = gr.Textbox(
            label="Results", 
            interactive=False, 
            lines=5, 
            max_lines=8)

└── Events: All buttons use queue=True for async operations
```

### Component Specifications

#### Upload Area (`self.upload_area`)
| Property | Value | Purpose |
|----------|-------|---------|
| `label` | "Upload Files" | Button/area label |
| `file_types` | List of extensions | Filters allowed file types |
| `type` | "binary" | Binary file data format |
| `interactive` | True | Drag & drop enabled |

**Supported File Extensions:**
- `.py`, `.js`, `.ts` - Code files
- `.html`, `.css` - Web files
- `.json`, `.txt` - Data and text files

#### Status Text (`self.status_text`)
| Property | Value |
|----------|-------|
| `label` | "Status" |
| `interactive` | False | Read-only status display |
| `value` | "Ready" | Initial state |

#### Action Buttons (`gr.Row`)
Four buttons for file operations.

| Button | Variant | Description |
|--------|---------|-------------|
| Upload Files | primary | Main action - uploads files |
| List Directory | secondary | Shows directory contents |
| Download File | secondary | Downloads available files |
| Create File | secondary | Creates new template file |

#### Results Text (`self.results_text`)
| Property | Value |
|----------|-------|
| `label` | "Results" |
| `interactive` | False | Read-only results display |
| `lines` | 5 | Initial height |
| `max_lines` | 8 | Maximum wrapping |

---

## Operations Overview

### Upload Files (Primary Action)
Uploads one or more files to the application.

**Process:**
1. User selects files via dialog or drag & drop
2. Files are saved to `uploads/` directory
3. Timestamp-based filenames prevent conflicts

**Output:**
```python
success_msg = f"✅ Uploaded {len(files)} file(s): [{file1}, {file2}...]"
return success_msg, success_msg + "\n\nFiles saved to: uploads/"
```

### List Directory
Shows the contents of the `data/github` directory.

**Display Format:**
```markdown
**Directory:** d:\rootme\sigmahqrag\data/github

**Files (5):**
  1. `main.py` - 2.5KB
  2. `utils.py` - 1.2KB
  3. `service.py` - 4.8KB
  4. `config.json` - 0.5KB
```

**Fallback:** If directory doesn't exist:
```
**Directory:** data/github
**Error:** Directory does not exist
```

### Download File
Lists available files for download.

**Output Format:**
```markdown
✅ Found X file(s) in data/github/

**Available files:**
- filepath1
- filepath2
...
```

### Create File
Creates a new template file with default content.

**File Details:**
- **Location:** `uploads/template_YYYYMMDD_HHMMSS.txt`
- **Default Content:**
  ```
  # New File
  Created: ISO_TIMESTAMP
  ```

---

## Upload Workflow

### File Selection
```python
for file_obj in files:
    filepath = Path(f"uploads/{timestamp}_{file_obj.name}")
```

### Save Operation
```python
with open(filepath, "wb") as f:
    f.write(file_obj.read())
```

**File Location:** `data/uploads/` - Files are stored with timestamp prefix to avoid conflicts.

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No files uploaded | Empty selection | Select files and try again |
| Upload failed | Disk space/full | Check available disk space |
| Invalid extension | File type not allowed | Use supported file types listed |
| Directory error | Path doesn't exist | Ensure data/github directory exists |

---

## Use Cases

### Code Review Preparation
1. **List Directory** - See what code files are available
2. **Download File** - Get specific file for offline review
3. **Upload Files** - Add new code samples to knowledge base

### Documentation Updates
1. **Upload Files** - Add documentation files (`.md`, `.rst`)
2. **List Directory** - Verify uploaded files appear in directory

### Template Creation
1. **Create File** - Generate a new template with timestamp
2. **Edit** - Open file and add your content

---

## Best Practices

1. **Use meaningful filenames** - Timestamp prefix ensures uniqueness
2. **Check before download** - List directory first to see available files
3. **Organize uploads** - Move uploaded files as needed after processing
4. **Verify uploads** - Check Results text to confirm successful upload

---

## File Locations

### Upload Destination
```
data/uploads/
├── YYYYMMDD_HHMMSS_filename.py
├── YYYYMMDD_HHMMSS_filename.txt
└── ...
```

### Directory Listing Source
```
data/github/
├── main.py
├── utils.py
└── ...
```

### Downloads Available
```python
files = list(Path("data/github").rglob("*"))
```

---

## Supported Formats

| Extension | Type | Description |
|-----------|------|-------------|
| `.py` | Python | Source code files |
| `.js` | JavaScript | JavaScript source files |
| `.ts` | TypeScript | TypeScript source files |
| `.html` | HTML | Web pages |
| `.css` | CSS | Stylesheets |
| `.json` | JSON | Data configuration files |
| `.txt` | Text | Plain text files |

---

## Related Documentation

- [📁 GitHub Tab](./tab_github.md) - Configure repositories to clone
- [📊 Data Tab](./tab_data.md) - Update the knowledge base
- [💬 Chat Tab](./tab_chat.md) - Ask questions about uploaded files
- [📋 USER MANUAL](./USER_MANUAL.md) - Complete application overview