"""
Data Page Implementation

Page for managing and displaying database information, including:
- Database statistics and information
- Update button for GitHub repositories
- Repository status display
"""

import asyncio
from nicegui import ui

from ..models.config_service import ConfigService
from ..models.data_service import DataService


class DataPage:
    """
    Data management page that displays database information and repository status.

    Attributes:
        data_service: Service for RAG operations
        config_service: Service for configuration management
        stats_container: UI element for displaying statistics
        progress_notification: Notification for update progress
    """

    def __init__(self):
        self.data_service = DataService()
        self.config_service = ConfigService()
        self.stats_container = None
        self.progress_notification = None

    def render(self):
        """
        Render the complete data management interface.

        Returns:
            The root element of the data page
        """
        # Main container with responsive layout
        main_container = ui.column().classes("w-full h-[70vh] bg-gray-100")

        with main_container:
            # Header
            self._render_header()

            # Statistics and Repository Status side by side
            self._render_side_by_side_content()

        # Load initial data
        asyncio.create_task(self._load_initial_data())

        return main_container

    def _render_header(self):
        """
        Render the data page header with title and controls.
        """
        with (
            ui.row()
            .classes("w-full bg-white border-b px-4 py-3 items-center justify-between")
            .style("box-shadow: 0 1px 2px rgba(0,0,0,0.05)")
        ):
            # Left side: Update database button
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    icon="cloud_download",
                    text="Update Database",
                    on_click=self._update_database,
                    color="primary",
                ).props("flat").tooltip(
                    "Update knowledge base from GitHub repositories"
                )

            # Right side: Refresh button
            ui.button(
                icon="refresh",
                text="Refresh",
                on_click=self._refresh_data,
                color="secondary",
            ).props("flat").tooltip("Refresh statistics and repository status")

    def _render_side_by_side_content(self):
        """
        Render the statistics and repository status side by side.
        """
        with ui.row().classes("w-full flex-1 gap-4 p-4"):
            # Database Statistics Card
            with ui.card().classes("flex-1 p-4"):
                ui.markdown("### Database Statistics")

                self.stats_container = ui.column().classes("gap-2")

                # Initial loading state
                with self.stats_container:
                    ui.label("Loading database statistics...").classes(
                        "text-sm text-gray-600"
                    )

            # Repository Status Card
            with ui.card().classes("flex-1 p-4"):
                ui.markdown("### Repository Status")

                self.repo_container = ui.column().classes("gap-2")

                # Initial loading state
                with self.repo_container:
                    ui.label("Loading repository information...").classes(
                        "text-sm text-gray-600"
                    )

    async def _load_initial_data(self):
        """
        Load initial data for statistics and repository status.
        """
        try:
            # Load database statistics
            stats = self.data_service.get_context_stats()
            self._update_statistics(stats)

            # Load repository information
            config_service = ConfigService()
            repo_config = config_service.get_repositories()
            self._update_repository_status(repo_config)

        except Exception as e:
            ui.notify(f"Error loading data: {str(e)}", type="negative")

    def _update_statistics(self, stats: dict):
        """
        Update the statistics display with current data.

        Args:
            stats: Dictionary containing database statistics
        """
        if self.stats_container:
            self.stats_container.clear()

            with self.stats_container:
                # Document count
                doc_count = stats.get("count", 0)
                ui.label(f"Total Documents: {doc_count:,}").classes("text-sm")

                # Database size
                db_size = stats.get("size_mb", 0)
                ui.label(f"Database Size: {db_size:.2f} MB").classes("text-sm")

                # Embedding model
                model = stats.get("embedding_model", "Unknown")
                ui.label(f"Embedding Model: {model}").classes("text-sm")

                # Chunking configuration
                chunk_size = stats.get("default_chunk_size", "Unknown")
                chunk_overlap = stats.get("default_chunk_overlap", "Unknown")
                ui.label(f"Chunk Size: {chunk_size} characters").classes("text-sm")
                ui.label(f"Chunk Overlap: {chunk_overlap} characters").classes(
                    "text-sm"
                )

    def _update_repository_status(self, repo_config):
        """
        Update the repository status display.

        Args:
            repo_config: Repository configuration data
        """
        if self.repo_container:
            self.repo_container.clear()

            with self.repo_container:
                # Total repositories
                total_repos = len(repo_config)
                enabled_repos = sum(1 for repo in repo_config if repo.enabled)

                ui.label(f"Total Repositories: {total_repos}").classes("text-sm")
                ui.label(f"Enabled Repositories: {enabled_repos}").classes("text-sm")

                # Repository list
                if repo_config:
                    ui.label("Repository List:").classes("text-sm font-medium mt-2")

                    for repo in repo_config:
                        status_color = (
                            "text-green-600" if repo.enabled else "text-gray-500"
                        )
                        status_text = "Enabled" if repo.enabled else "Disabled"

                        with ui.row().classes("items-center gap-2"):
                            ui.icon("circle").classes(f"w-2 h-2 {status_color}")
                            ui.label(f"{repo.url} ({repo.branch})").classes("text-sm")
                            ui.label(f"[{status_text}]").classes(
                                f"text-xs {status_color}"
                            )
                else:
                    ui.label("No repositories configured").classes(
                        "text-sm text-gray-500"
                    )

    async def _refresh_data(self):
        """
        Refresh the statistics and repository status display.
        """
        try:
            # Show refresh notification
            refresh_notification = ui.notification(
                message="Refreshing data...", spinner=True, timeout=None
            )

            # Load database statistics
            stats = self.data_service.get_context_stats()
            self._update_statistics(stats)

            # Load repository information
            config_service = ConfigService()
            repo_config = config_service.get_repositories()
            self._update_repository_status(repo_config)

            # Update notification with success
            refresh_notification.message = "Data refreshed successfully!"
            refresh_notification.spinner = False
            await asyncio.sleep(2)
            refresh_notification.dismiss()

        except Exception as e:
            ui.notify(f"Error refreshing data: {str(e)}", type="negative")

    async def _update_database(self):
        """
        Update the knowledge base by indexing enabled GitHub repositories.
        Shows progress notification and runs the update process in the background.
        """
        # Create a persistent notification for progress updates
        self.progress_notification = ui.notification(timeout=None)

        # Start the background update process
        asyncio.create_task(self._update_database_with_progress())

    async def _update_database_with_progress(self):
        """
        Background task to update the knowledge base with progress notifications.
        Uses multithreading to prevent blocking the main application.
        """
        try:
            # Step 1: Load configuration
            self.progress_notification.message = "Loading configuration..."
            self.progress_notification.spinner = True

            config_service = ConfigService()
            repo_config = config_service.get_repositories()

            # Convert RepositoryConfig objects to dict format
            repo_dict = {
                "repositories": [
                    {
                        "url": repo.url,
                        "branch": repo.branch,
                        "enabled": repo.enabled,
                        "file_extensions": repo.file_extensions,
                    }
                    for repo in repo_config
                ]
            }

            enabled_repos = [repo for repo in repo_config if repo.enabled]

            if not enabled_repos:
                self.progress_notification.message = (
                    "No enabled repositories found in configuration."
                )
                self.progress_notification.spinner = False
                await asyncio.sleep(2)
                self.progress_notification.dismiss()
                return

            # Step 2: Clone repositories (Step 1/2)
            self.progress_notification.message = (
                f"Step 1/2: Updating {len(enabled_repos)} repositories..."
            )
            self.progress_notification.spinner = True

            # Run clone operation in thread pool
            import concurrent.futures

            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit clone task to thread pool
                clone_future = executor.submit(
                    self.data_service.clone_enabled_repositories, repo_dict
                )

                # Wait for clone to complete with timeout
                try:
                    clone_result = await asyncio.wait_for(
                        loop.run_in_executor(None, clone_future.result),
                        timeout=300,  # 5 minute timeout
                    )
                except asyncio.TimeoutError:
                    self.progress_notification.message = (
                        "Repository cloning timed out. Please try again."
                    )
                    self.progress_notification.spinner = False
                    await asyncio.sleep(3)
                    self.progress_notification.dismiss()
                    return

            if not clone_result:
                self.progress_notification.message = (
                    "Failed to update repositories. Please check the configuration."
                )
                self.progress_notification.spinner = False
                await asyncio.sleep(3)
                self.progress_notification.dismiss()
                return

            # Step 3: Index repositories (Step 2/2)
            self.progress_notification.message = (
                "Step 2/2: Indexing repository content..."
            )
            self.progress_notification.spinner = True

            # Run indexing operation in thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit index task to thread pool
                index_future = executor.submit(
                    self.data_service.index_enabled_repositories, repo_dict
                )

                # Wait for indexing to complete with timeout
                try:
                    index_result = await asyncio.wait_for(
                        loop.run_in_executor(None, index_future.result),
                        timeout=600,  # 10 minute timeout
                    )
                except asyncio.TimeoutError:
                    self.progress_notification.message = (
                        "Indexing timed out. Please try again."
                    )
                    self.progress_notification.spinner = False
                    await asyncio.sleep(3)
                    self.progress_notification.dismiss()
                    return

            if index_result:
                # Get context stats for detailed feedback
                stats = self.data_service.get_context_stats()
                total_docs = stats.get("count", 0)
                self.progress_notification.message = (
                    f"✅ Knowledge base updated successfully! "
                    f"Indexed {total_docs} documents from {len(enabled_repos)} repositories."
                )
                self.progress_notification.spinner = False
                await asyncio.sleep(3)
                self.progress_notification.dismiss()

                # Refresh the display
                await self._load_initial_data()
            else:
                self.progress_notification.message = (
                    "No repositories were indexed. Please check the configuration."
                )
                self.progress_notification.spinner = False
                await asyncio.sleep(3)
                self.progress_notification.dismiss()

        except Exception as e:
            error_msg = f"Error updating knowledge base: {str(e)}"
            self.progress_notification.message = error_msg
            self.progress_notification.spinner = False
            await asyncio.sleep(3)
            self.progress_notification.dismiss()
