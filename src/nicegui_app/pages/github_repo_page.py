"""
GitHub Repository Management Page with AG Grid
Complete rewrite using AG Grid for all CRUD operations based on NiceGUI example
"""

import asyncio
from typing import Any

from nicegui import ui

# Import modern components
from ..components.notification import notify

# Import ConfigService and RepositoryConfig
from ..models.config_service import ConfigService, RepositoryConfig

# Global state
grid = None


def load_config() -> dict[str, Any]:
    """Load configuration from file using ConfigService"""
    try:
        config_service = ConfigService()
        config_data = config_service.get_repositories()

        # Convert RepositoryConfig objects to dicts
        repositories = [
            {
                "url": repo.url,
                "branch": repo.branch,
                "enabled": repo.enabled,
                "file_extensions": repo.file_extensions,
            }
            for repo in config_data
        ]

        return {"repositories": repositories}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"repositories": []}


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file using ConfigService"""
    try:
        config_service = ConfigService()

        # Convert dict to RepositoryConfig objects
        repositories = [
            RepositoryConfig(
                url=repo["url"],
                branch=repo["branch"],
                enabled=repo["enabled"],
                file_extensions=repo.get("file_extensions", []),
            )
            for repo in config.get("repositories", [])
        ]

        config_service.update_repositories(repositories)
    except Exception as e:
        print(f"Error saving config: {e}")


def is_duplicate(url: str, branch: str, exclude_index: int = -1) -> bool:
    """Check if repository URL+branch combination already exists"""
    if grid is None or not hasattr(grid, "options"):
        return False

    for i, repo in enumerate(grid.options["rowData"]):
        if i == exclude_index:
            continue
        if (
            repo.get("url", "").lower() == url.lower()
            and repo.get("branch", "").lower() == branch.lower()
        ):
            return True
    return False


def add_new_repository():
    """Add a new empty row for adding a repository"""
    if not grid or not hasattr(grid, "options"):
        return

    new_id = max((dx["id"] for dx in grid.options["rowData"]), default=-1) + 1
    new_row = {
        "id": new_id,
        "url": "",
        "branch": "",
        "extensions": "None",
        "enabled": True,
    }
    grid.options["rowData"].append(new_row)
    notify(f"Added row with ID {new_id}")
    # Force a full refresh of the grid data
    grid.options = grid.options.copy()
    grid.update()
    # Additional refresh to ensure the grid renders the new row
    ui.run_javascript(
        "setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 100)"
    )


def save_edits():
    """Save all edits made to the grid to config file"""
    try:
        # Get current data from grid
        if not grid or not hasattr(grid, "options"):
            notify("Grid not initialized!", type="negative")
            return

        grid_data = grid.options["rowData"]

        if not grid_data:
            notify("No changes to save!", type="info")
            return

        # Validate enabled state
        for row in grid_data:
            if not isinstance(row.get("enabled"), bool):
                notify("Invalid Enabled state!", type="negative")
                return

        # Load existing config and update with grid data
        config = load_config()
        config["repositories"] = []

        for row in grid_data:
            # Skip rows with empty URL and branch (new rows)
            if not row.get("url") or not row.get("branch"):
                continue

            extensions_list = [
                ext.strip()
                for ext in row.get("extensions", "").split(",")
                if ext.strip() and ext.strip() != "None"
            ]
            config["repositories"].append(
                {
                    "url": row["url"],
                    "branch": row["branch"],
                    "enabled": row["enabled"],
                    "file_extensions": extensions_list,
                }
            )

        save_config(config)
        notify("Changes saved successfully!", type="positive")
    except Exception as e:
        notify(f"Error saving changes: {e}", type="negative")


async def remove_selected():
    """Remove selected rows from the grid"""
    if not grid or not hasattr(grid, "options"):
        return

    try:
        # Get selected rows - this returns a coroutine that needs to be awaited
        selected_rows = await grid.get_selected_rows()
        if not selected_rows:
            notify("No rows selected!", type="warning")
            return

        # Remove selected rows from grid data
        selected_ids = {row["id"] for row in selected_rows}
        grid.options["rowData"] = [
            row for row in grid.options["rowData"] if row["id"] not in selected_ids
        ]

        # Update IDs after removal
        for i, row in enumerate(grid.options["rowData"]):
            row["id"] = i

        grid.update()
        notify(f"Deleted {len(selected_ids)} repository(ies)!", type="positive")
    except Exception as e:
        notify(f"Error deleting repositories: {e}", type="negative")


async def update_all_enabled_repos():
    """Update all enabled repositories"""
    from ..models.data_service import DataService

    notify("Updating repositories...")
    try:
        config = load_config()
        data_service = DataService()
        success = await asyncio.to_thread(
            data_service.clone_enabled_repositories, config
        )

        if success:
            notify("Update completed!", type="positive")
        else:
            notify("Update failed", type="negative")
    except Exception as e:
        notify(f"Error: {e}", type="negative")


def initialize_page():
    """Initialize the GitHub repository management page"""
    global grid

    with ui.column().classes("w-full  bg-gray-100"):
        # Header
        with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center"):
            ui.label("GitHub Repository Management").classes("text-lg font-semibold text-gray-800")
            ui.element("div").classes("flex-1")

        # Main content area - use flex to fill available space
        with ui.column().classes("w-full p-4 gap-4 flex-1"):
            # Action buttons
            with ui.row().classes("gap-3 flex-wrap"):
                ui.button(
                    icon="add",
                    text="Add New",
                    on_click=add_new_repository,
                ).props("flat")
                ui.button(
                    icon="save",
                    text="Save",
                    on_click=save_edits,
                    color="primary",
                ).props("flat")
                ui.button(
                    icon="delete",
                    text="Delete Selected",
                    color="negative",
                ).props(
                    "flat"
                ).on_click(lambda: remove_selected())
                ui.button(
                    icon="update",
                    text="UPDATE ALL",
                    on_click=lambda: update_all_enabled_repos(),
                    color="primary",
                ).props("flat")

            # AG Grid Table - use flex to fill available space
            with ui.card().classes("w-full p-4 flex-1"):
                column_defs = [
                    {"field": "url", "editable": True},
                    {"field": "branch", "editable": True},
                    {"field": "extensions", "editable": True},
                    {
                        "field": "enabled",
                        "cellRenderer": "agCheckboxCellRenderer",
                        "editable": True,
                    },
                ]

                # Load initial data from config
                config = load_config()
                grid_rows = []

                for idx, repo in enumerate(config["repositories"]):
                    ext_text = (
                        ", ".join(repo["file_extensions"])
                        if repo.get("file_extensions")
                        else "None"
                    )
                    grid_rows.append(
                        {
                            "id": idx,
                            "url": repo["url"],
                            "branch": repo["branch"],
                            "extensions": ext_text,
                            "enabled": repo["enabled"],
                        }
                    )

                grid = (
                    ui.aggrid(
                        {
                            "columnDefs": column_defs,
                            "rowData": grid_rows,
                            "pagination": True,
                            "paginationPageSize": 10,
                            "editType": "fullRow",
                            "rowSelection": {"mode": "multiRow"},
                            "domLayout": "normal",
                            "animateRows": True,
                            "rowHeight": 40,
                            "headerHeight": 50,
                            "responsive": True,
                        }
                    )
                    .classes("w-full h-full")
                    .on("cellValueChanged", handle_cell_edit)
                )


def handle_cell_edit(e):
    """Handle cell edit events from AG Grid"""
    try:
        new_row = e.args["data"]
        notify(f'Updated row to: {e.args["data"]}')
        grid.options["rowData"][:] = [
            row | new_row if row["id"] == new_row["id"] else row
            for row in grid.options["rowData"]
        ]
        grid.update()
    except Exception as e:
        notify(f"Error handling cell edit: {e}", type="negative")
