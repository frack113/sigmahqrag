"""
GitHub Repository Management Page
Handles adding, removing, and updating GitHub repositories for indexing.
"""
from typing import List, Dict, Any
import json
import os
from pathlib import Path
from nicegui import ui


def load_config() -> Dict[str, Any]:
    """Load the GitHub repository configuration from /config/github.json."""
    config_path = Path("config/github.json")
    if not config_path.exists():
        return {"repositories": []}

    with open(config_path, "r") as file:
        try:
            return json.load(file) or {"repositories": []}
        except (json.JSONDecodeError, FileNotFoundError):
            return {"repositories": []}

def save_config(config: Dict[str, Any]) -> None:
    """Save the GitHub repository configuration to /config/github.json."""
    config_path = Path("config/github.json")
    os.makedirs(config_path.parent, exist_ok=True)

    with open(config_path, "w") as file:
        json.dump(config, file, indent=4)

def add_repository() -> None:
    """Add a new repository to the configuration."""
    url = ui.input("URL", placeholder="https://github.com/user/repo").value
    branch = ui.input("Branch", placeholder="main").value
    enabled = True  # Default to enabled
    extensions = [ext.strip() for ext in ui.input("File Extensions (comma-separated)", placeholder=".md, .py").value.split(",") if ext.strip()]

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
    url = ui.input("URL", placeholder="https://github.com/user/repo").value
    branch = ui.input("Branch", placeholder="main").value
    enabled = True  # Default to enabled
    extensions = [ext.strip() for ext in ui.input("File Extensions (comma-separated)", placeholder=".md, .py").value.split(",") if ext.strip()]

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

def refresh_repository_list() -> None:
    """Refresh the list of repositories."""
    repositories = load_config()["repositories"]
    repo_list.clear()

    for idx, repo in enumerate(repositories):
        with ui.card().classes("w-full max-w-md m-2"):
            ui.label(f"Repository {idx + 1}").classes("text-lg font-bold")
            ui.input("URL", value=repo["url"]).props("readonly").classes("mb-2")
            ui.input("Branch", value=repo["branch"]).props("readonly").classes("mb-2")

            # Enable toggle (slider)
            slider = ui.toggle([
                {"label": "Disabled", "value": False},
                {"label": "Enabled", "value": True}
            ]).bind_value(repo, "enabled").on("update:model-value", lambda e: save_config(load_config()))

            # File extensions (multiselect)
            ui.label("File Extensions:")
            for ext in repo["file_extensions"]:
                ui.input(f"Extension {len(repo['file_extensions']) + 1}", value=ext).props("readonly").classes("mb-1")

            # Action buttons
            with ui.row().classes("mt-2"):
                ui.button("Update", on_click=lambda: update_repository(idx)).classes("q-mr-sm")
                ui.button("Remove", on_click=lambda: remove_repository(idx), color="negative").classes("q-mr-sm")

# Initialize the page
repo_list = None

def initialize_page() -> None:
    global repo_list
    
    with ui.card():
        ui.label("GitHub Repository Management").classes("text-h5")
        # Add new repository form
        with ui.expansion("Add New Repository", icon="add"):
            ui.input("URL", placeholder="https://github.com/user/repo").classes("mb-2")
            ui.input("Branch", placeholder="main").classes("mb-2")
            ui.input("File Extensions (comma-separated)", placeholder=".md, .py").classes("mb-2")
            ui.button("Add Repository", on_click=add_repository).classes("q-mr-sm")

        # List of repositories
        with ui.expansion("Repository List", icon="list"):
            repo_list = ui.column()
            refresh_repository_list()

# Start the page
initialize_page()