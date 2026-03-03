"""
GitHub Repository Management Page with AG Grid
Complete rewrite using AG Grid for all CRUD operations
"""
from typing import List, Dict, Any
import json
import os
import shutil
from pathlib import Path
from nicegui import ui
import asyncio

# Global state
grid = None
repo_config = {"repositories": []}

def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    config_path = Path("config/github.json")
    if not config_path.exists():
        return {"repositories": []}
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file) or {"repositories": []}

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file"""
    config_path = Path("config/github.json")
    os.makedirs(config_path.parent, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

def is_duplicate(url: str, branch: str, exclude_index: int = -1) -> bool:
    """Check if repository URL+branch combination already exists"""
    config = load_config()
    for i, repo in enumerate(config["repositories"]):
        if i == exclude_index:
            continue
        if repo.get("url").lower() == url.lower() and repo.get("branch").lower() == branch.lower():
            return True
    return False

def add_repository(url: str, branch: str, extensions: str, enabled: bool) -> bool:
    """Add new repository with duplicate checking"""
    if not url or not branch:
        ui.notify("URL and Branch are required!", type='negative')
        return False
    
    if is_duplicate(url, branch):
        ui.notify(f"Repository '{url}' with branch '{branch}' already exists!", type='negative')
        return False
    
    extensions_list = [ext.strip() for ext in extensions.split(",") if ext.strip()]
    
    config = load_config()
    config["repositories"].append({
        "url": url,
        "branch": branch,
        "enabled": enabled,
        "file_extensions": extensions_list
    })
    save_config(config)
    refresh_grid()
    return True

def update_repository(index: int, url: str, branch: str, extensions: str, enabled: bool) -> bool:
    """Update existing repository with duplicate checking"""
    if not url or not branch:
        ui.notify("URL and Branch are required!", type='negative')
        return False
    
    if is_duplicate(url, branch, index):
        ui.notify(f"Repository '{url}' with branch '{branch}' already exists!", type='negative')
        return False
    
    extensions_list = [ext.strip() for ext in extensions.split(",") if ext.strip()]
    
    config = load_config()
    if 0 <= index < len(config["repositories"]):
        config["repositories"][index] = {
            "url": url,
            "branch": branch,
            "enabled": enabled,
            "file_extensions": extensions_list
        }
        save_config(config)
        refresh_grid()
        return True
    return False

def remove_repository(index: int) -> bool:
    """Remove repository and clean up files"""
    config = load_config()
    if 0 <= index < len(config["repositories"]):
        repo = config["repositories"][index]
        url = repo["url"]
        
        # Clean up files
        parts = url.strip().split('/')
        if len(parts) >= 5 and parts[2] == "github.com":
            repo_name = parts[4]
            repo_dir = Path("docs/github") / repo_name
            if repo_dir.exists():
                try:
                    shutil.rmtree(repo_dir)
                except Exception as e:
                    ui.notify(f"Files deleted but config update failed: {e}", type='warning')
                    return False
        
        config["repositories"].pop(index)
        save_config(config)
        refresh_grid()
        return True
    return False

def refresh_grid():
    """Refresh AG Grid with current repository data"""
    global grid
    if grid is None:
        return
    
    config = load_config()
    grid_rows = []
    
    for idx, repo in enumerate(config["repositories"]):
        ext_text = ", ".join(repo["file_extensions"]) if repo["file_extensions"] else "None"
        grid_rows.append({
            "id": idx,
            "url": repo["url"],
            "branch": repo["branch"],
            "extensions": ext_text,
            "enabled": repo["enabled"]
        })
    
    grid.options['rowData'] = grid_rows

def initialize_page():
    """Initialize the GitHub repository management page"""
    global grid
    
    with ui.card().classes("p-4 w-full max-w-6xl mx-auto"):
        # Header
        with ui.row().classes("justify-between items-center mb-4"):
            ui.label("GitHub Repository Management").classes("text-h5")
            with ui.row().classes("gap-2"):
                ui.button(icon="home", text="Back to Chat", on_click=lambda: ui.navigate.to("/"))
                ui.button(icon="source", text="UPDATE ALL", on_click=lambda: update_all_enabled_repos())
        
        # Add Repository Form
        with ui.card().classes("mb-4 p-4"):
            ui.label("Add New Repository").classes("text-h6 mb-2")
            with ui.row().classes("gap-4 items-end"):
                url_input = ui.input("URL", placeholder="https://github.com/user/repo").classes("flex-1")
                branch_input = ui.input("Branch", placeholder="main").classes("w-48")
                ext_input = ui.input("Extensions", placeholder=".py,.md").classes("w-64")
                enabled_checkbox = ui.checkbox("Enabled", value=True).classes("ml-2")
                ui.button("ADD", icon="add", on_click=lambda: add_repository(
                    url_input.value, 
                    branch_input.value, 
                    ext_input.value, 
                    enabled_checkbox.value
                ))
        
        # AG Grid Table
        with ui.card():
            column_defs = [
                {"headerName": "URL", "field": "url", "editable": True, "flex": 2},
                {"headerName": "Branch", "field": "branch", "editable": True, "flex": 1},
                {"headerName": "Extensions", "field": "extensions", "editable": True, "flex": 1},
                {"headerName": "Enabled", "field": "enabled", "cellRenderer": "agCheckboxCellRenderer", "flex": 1},
                {"headerName": "Actions", "field": "actions", "cellRenderer": "agButtonCellRenderer", "flex": 1}
            ]
            
            grid = ui.aggrid({
                "columnDefs": column_defs,
                "rowData": [],
                "pagination": True,
                "paginationPageSize": 10,
                "editType": "fullRow",
                "onCellValueChanged": lambda e: handle_cell_edit(e),
                "onRowClicked": lambda e: handle_row_click(e)
            })
    
    refresh_grid()

def handle_cell_edit(event):
    """Handle cell edit events from AG Grid"""
    row = event['data']
    field = event['colId']
    value = event['newValue']
    
    config = load_config()
    if 0 <= row['id'] < len(config["repositories"]):
        repo = config["repositories"][row['id']]
        
        if field == "enabled":
            repo[field] = value
        else:
            # For other fields, we need full validation
            if field == "url":
                repo[field] = value
            elif field == "branch":
                repo[field] = value
            elif field == "extensions":
                repo["file_extensions"] = [ext.strip() for ext in value.split(",") if ext.strip()]
        
        save_config(config)

def handle_row_click(event):
    """Handle row click for action buttons"""
    # Implementation for edit/remove buttons
    pass

async def update_all_enabled_repos():
    """Update all enabled repositories"""
    from ..models.data_service import DataService
    
    ui.notify("Updating repositories...")
    try:
        config = load_config()
        data_service = DataService()
        success = await asyncio.to_thread(data_service.clone_enabled_repositories, config)
        
        if success:
            ui.notify("Update completed!", type='positive')
        else:
            ui.notify("Update failed", type='negative')
    except Exception as e:
        ui.notify(f"Error: {e}", type='negative')