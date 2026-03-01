"""
GitHub Repository Management Page
Handles adding, removing, and updating GitHub repositories for indexing.
"""
from typing import List, Dict, Any
import json
import os
from pathlib import Path
from nicegui import ui
import asyncio


def load_config() -> Dict[str, Any]:
    """Load the GitHub repository configuration from /config/github.json."""
    config_path = Path("config/github.json")
    if not config_path.exists():
        return {"repositories": []}

    with open(config_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file) or {"repositories": []}
        except (json.JSONDecodeError, FileNotFoundError):
            return {"repositories": []}


def fetch_github_repositories() -> List[Dict[str, Any]]:
    """Fetch GitHub repositories using the data service."""
    from ..models.data_service import DataService
    
    try:
        repo_config = load_config()
        if not repo_config.get("repositories"):
            return []
        
        data_service = DataService()
        repositories = data_service.fetch_github_repositories(repo_config)
        return repositories
    except Exception as e:
        ui.notify(f"Error fetching repositories: {e}", type='negative')
        return []

def save_config(config: Dict[str, Any]) -> None:
    """Save the GitHub repository configuration to /config/github.json."""
    config_path = Path("config/github.json")
    os.makedirs(config_path.parent, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

def add_repository() -> None:
    """Add a new repository to the configuration."""
    url = ui.input("URL").value
    branch = ui.input("Branch").value
    enabled = True  # Default to enabled
    extensions = [ext.strip() for ext in ui.input("File Extensions (comma-separated)").value.split(",") if ext.strip()]

    repositories = load_config()["repositories"]
    repositories.append({
        "url": url,
        "branch": branch,
        "enabled": enabled,
        "file_extensions": extensions
    })
    save_config({"repositories": repositories})
    ui.notify("Repository added successfully!")
    refresh_repository_list()

def remove_repository(index: int) -> None:
    """Remove a repository from the configuration."""
    repositories = load_config()["repositories"]
    if 0 <= index < len(repositories):
        removed_url = repositories.pop(index)["url"]
        save_config({"repositories": repositories})
        ui.notify(f"Repository '{removed_url}' removed successfully!")
        refresh_repository_list()

def update_repository(index: int) -> None:
    """Update an existing repository in the configuration."""
    url = ui.input("URL").value
    branch = ui.input("Branch").value
    enabled = True  # Default to enabled
    extensions = [ext.strip() for ext in ui.input("File Extensions (comma-separated)").value.split(",") if ext.strip()]

    repositories = load_config()["repositories"]
    if 0 <= index < len(repositories):
        repositories[index] = {
            "url": url,
            "branch": branch,
            "enabled": enabled,
            "file_extensions": extensions
        }
        save_config({"repositories": repositories})
        ui.notify("Repository updated successfully!")
        refresh_repository_list()

def _update_repo_enabled(repo: dict, enabled: bool) -> None:
    """Update repository enabled status."""
    repositories = load_config()["repositories"]
    for i, r in enumerate(repositories):
        if r.get("url") == repo.get("url"):
            repositories[i]["enabled"] = enabled
            save_config({"repositories": repositories})
            break


def refresh_repository_list() -> None:
    """Refresh the list of repositories."""
    # Load repositories from config directly for display
    repo_config = load_config()
    repositories = repo_config.get("repositories", [])
    
    if repo_list is not None:
        repo_list.clear()
    else:
        return  # repo_list not initialized yet
    
    # Table header - desktop view
    with ui.row().classes("font-bold mb-2 bg-gray-50 p-2 border-b w-full items-center"):
        with ui.column().classes("w-[24%] pl-2 text-gray-700"):
            ui.label("URL")
        with ui.column().classes("w-[14%] px-2 text-gray-700"):
            ui.label("Branch")
        with ui.column().classes("w-[24%] px-2 text-gray-700"):
            ui.label("File Extension")
        with ui.column().classes("w-[14%] text-center px-2 text-gray-700"):
            ui.label("Enabled")
        with ui.column().classes("w-[14%] text-right pr-2 text-gray-700"):
            ui.label("Actions")
    
    if not repositories:
        repo_list.add(ui.label("No repositories configured yet.").classes("text-gray-500"))
        return
    
    # Table rows - desktop view
    for idx, repo in enumerate(repositories):
        with ui.card().classes("mb-2 w-full overflow-hidden"):
            with ui.row().classes("items-center p-2 w-full"):
                with ui.column().classes("w-[24%] overflow-hidden text-ellipsis pl-2"):
                    ui.label(repo["url"]).classes("text-sm")
                with ui.column().classes("w-[14%] px-2"):
                    ui.label(repo["branch"]).classes("text-sm")
                with ui.column().classes("w-[24%] overflow-hidden text-ellipsis px-2"):
                    ext_text = ", ".join(repo["file_extensions"]) if repo["file_extensions"] else "None"
                    ui.label(ext_text).classes("text-sm")
                with ui.column().classes("w-[14%] items-center justify-center px-2"):
                    ui.switch(
                        value=repo.get("enabled", False),
                        on_change=lambda e, r=repo: _update_repo_enabled(r, e.value)
                    ).props("dense")
                with ui.column().classes("w-[14%] justify-end gap-2 pr-2"):
                    ui.button(icon="edit_document", on_click=lambda: update_repository(idx)).props("flat dense size=sm")
                    ui.button(icon="delete_outline", on_click=lambda: remove_repository(idx), color="negative").props("flat dense size=sm")

# Initialize the page
repo_list = None

def initialize_page() -> None:
    """Initialize the GitHub repository management page UI."""
    global repo_list
    
    with ui.card().classes("p-4 w-full max-w-6xl mx-auto"):
        # Header with buttons
        with ui.row().classes("justify-between items-center mb-4"):
            ui.label("GitHub Repository Management").classes("text-h5")
            with ui.row().classes("gap-2"):
                ui.button(icon="home", text="Back to Chat", on_click=lambda: ui.navigate.to("/")).classes("ml-2")
                # Update all enabled repositories button
                update_button = ui.button(icon="source", text="UPDATE").classes("ml-2")
                update_button.on_click(lambda: update_all_enabled_repos())
        
        # Add new repository form
        with ui.row().classes("mb-4 items-center gap-4 w-full"):
            url_input = ui.input("URL").classes("flex-1")
            branch_input = ui.input("Branch").classes("w-64")
            ext_input = ui.input("File Extensions (comma-separated)").classes("w-80")
            add_button = ui.button(icon="add_box", text="Add Repository").classes("min-w-[120px]")
            add_button.on_click(add_repository)
        
        # List of repositories
        with ui.card().classes("w-full"):
            ui.label("Repository List").classes("text-subtitle1 mb-2")
            if repo_list is None:
                repo_list = ui.column()
            
            # Load repositories when page loads
            refresh_repository_list()

async def update_all_enabled_repos() -> None:
    """Update all enabled repositories in the background."""
    from ..models.data_service import DataService
    
    ui.notify("Updating enabled repositories...", type='info')
    
    try:
        repo_config = load_config()
        data_service = DataService()
        success = await asyncio.to_thread(data_service.clone_enabled_repositories, repo_config)
        
        if success:
            ui.notify("All enabled repositories updated successfully!", type='positive')
        else:
            ui.notify("Failed to update some repositories.", type='negative')
    except Exception as e:
        ui.notify(f"Error updating repositories: {e}", type='negative')