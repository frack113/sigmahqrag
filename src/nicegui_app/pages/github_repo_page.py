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

def fetch_github_repositories() -> List[Dict[str, Any]]:
    """Fetch GitHub repositories using the data service."""
    from ..models.data_service import DataService
    
    try:
        if not grid or not hasattr(grid, 'options') or not grid.options.get('rowData'):
            return []
        
        repo_config = {"repositories": grid.options['rowData']}
        data_service = DataService()
        repositories = data_service.fetch_github_repositories(repo_config)
        return repositories
    except Exception as e:
        ui.notify(f"Error fetching repositories: {e}", type='negative')
        return []

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
    if not grid or not hasattr(grid, 'options') or not grid.options.get('rowData'):
        return False
    
    for i, repo in enumerate(grid.options['rowData']):
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
    
    if not grid or not hasattr(grid, 'options'):
        grid.options = {'rowData': []}
    
    new_id = len(grid.options['rowData'])
    grid.options['rowData'].append({
        "id": new_id,
        "url": url,
        "branch": branch,
        "extensions": extensions if extensions else "None",
        "enabled": enabled
    })
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
    
    if not grid or not hasattr(grid, 'options') or index >= len(grid.options['rowData']):
        return False
    
    grid.options['rowData'][index] = {
        "id": index,
        "url": url,
        "branch": branch,
        "extensions": extensions if extensions else "None",
        "enabled": enabled
    }
    return True

def remove_repository(index: int) -> bool:
    """Remove repository and clean up files with error handling"""
    try:
        if not grid or not hasattr(grid, 'options') or index >= len(grid.options['rowData']):
            return False
        
        repo = grid.options['rowData'][index]
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
                    ui.notify(f"Error deleting files: {e}", type='negative')
                    return False
        
        grid.options['rowData'].pop(index)
        # Update IDs after removal
        for i, row in enumerate(grid.options['rowData']):
            if 'id' in row:
                row['id'] = i
        
        return True
    except Exception as e:
        ui.notify(f"Error removing repository: {e}", type='negative')
        return False

def refresh_grid():
    """Refresh AG Grid with current repository data"""
    global grid
    if grid is None or not hasattr(grid, 'options'):
        return
    
    config = load_config()
    grid_rows = []
    
    for idx, repo in enumerate(config["repositories"]):
        ext_text = ", ".join(repo["file_extensions"]) if repo.get("file_extensions") else "None"
        grid_rows.append({
            "id": idx,
            "url": repo["url"],
            "branch": repo["branch"],
            "extensions": ext_text,
            "enabled": repo["enabled"]
        })
    
    grid.options['rowData'] = grid_rows

def add_new_repository():
    """Add a new empty row for adding a repository - updates only grid data"""
    # Add directly to grid - no config modification
    if not grid or not hasattr(grid, 'options'):
        return
    
    new_id = len(grid.options['rowData'])
    ext_text = "None"
    grid.options['rowData'].append({
        "id": new_id,
        "url": "",
        "branch": "",
        "extensions": ext_text,
        "enabled": True
    })

def save_edits():
    """Save all edits made to the grid to config file with file cleanup"""
    try:
        # Get current data from grid
        if not grid or not hasattr(grid, 'options'):
            ui.notify("Grid not initialized!", type='negative')
            return
        
        grid_data = grid.options['rowData']
        
        if not grid_data:
            ui.notify("No changes to save!", type='info')
            return
        
        # Validate enabled state
        for row in grid_data:
            if not isinstance(row.get("enabled"), bool):
                ui.notify("Invalid Enabled state!", type='negative')
                return
        
        # Load existing config and update with grid data
        config = load_config()
        config["repositories"] = []
        
        for row in grid_data:
            extensions_list = [ext.strip() for ext in row.get("extensions", "").split(",") if ext.strip()]
            config["repositories"].append({
                "url": row["url"],
                "branch": row["branch"],
                "enabled": row["enabled"],
                "file_extensions": extensions_list
            })
        
        save_config(config)
        ui.notify("Changes saved successfully!", type='positive')
    except Exception as e:
        ui.notify(f"Error saving changes: {e}", type='negative')

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
        
        # Delete button for selected rows
        with ui.row().classes("mt-4"):
            add_bouton = ui.button(icon="add", text="Add New", on_click=lambda: add_new_repository())
            save_button = ui.button(icon="save", text="Save", on_click=lambda: save_edits())
            delete_button = ui.button(icon="delete", text="Delete Selected", color="red").on_click(lambda: delete_selected_rows(grid))

        
        # AG Grid Table
        with ui.card().classes("w-full"):
            column_defs = [
                {"headerName": "URL", "field": "url", "editable": True, "flex": 2},
                {"headerName": "Branch", "field": "branch", "editable": True, "flex": 1},
                {"headerName": "Extensions", "field": "extensions", "editable": True, "flex": 1},
                {"headerName": "Enabled", "field": "enabled", "cellRenderer": "agCheckboxCellRenderer", "editable": True,"flex": 1}
            ]
            
            grid = ui.aggrid({
                "columnDefs": column_defs,
                "rowData": [],
                "pagination": True,
                "paginationPageSize": 10,
                "editType": "fullRow",
                "rowSelection": {"mode": "multiRow"}
            }).classes("w-full").on('cellEdit', handle_cell_edit)
    
    refresh_grid()



def handle_cell_edit(event):
    """Handle cell edit events from AG Grid - updates only in memory, not saved to disk"""
    try:
        row = event['data']
        field = event['colId']
        value = event['newValue']
        
        # Get the current config (this will be saved later when user clicks Save)
        if 0 <= row['id'] < len(grid.options['rowData']):
            # Update the grid data directly
            grid.options['rowData'][row['id']][field] = value
    except Exception as e:
        ui.notify(f"Error handling cell edit: {e}", type='negative')

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

async def delete_selected_rows(grid):
    """Delete selected rows from AG Grid with confirmation"""
    # Create a dialog for confirmation
    dialog = ui.dialog()
    with dialog, ui.card().classes('p-4'):
        ui.label("Are you sure you want to delete the selected repositories?").classes('text-lg font-semibold')
        with ui.row().classes('justify-end mt-4 gap-2'):
            ui.button('Cancel', on_click=dialog.close).props('outline')
            ui.button('Delete', color='red', on_click=lambda: confirm_delete(grid, dialog))
    
    # Show the dialog
    dialog.open()

async def confirm_delete(grid, dialog):
    """Handle confirmed deletion after dialog is closed - updates only grid data"""
    try:
        selected_rows = await grid.get_selected_rows()
        if not selected_rows:
            ui.notify("No rows selected!", type='warning')
            return
        
        deleted_count = 0
        
        # Delete from grid data only - file cleanup handled in save_edits
        current_rows = grid.options['rowData'][:]
        grid.options['rowData'] = [row for row in current_rows if row['id'] not in [r['id'] for r in selected_rows]]
        deleted_count = len(selected_rows)
        
        ui.notify(f"Deleted {deleted_count} repository(ies)!", type='positive')
    except Exception as e:
        ui.notify(f"Error deleting repositories: {e}", type='negative')
    finally:
        dialog.close()