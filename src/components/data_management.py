"""
Data Management Component for Gradio

Migrates the Data page to Gradio with async background operations
for database updates and repository management.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import gradio as gr
from src.models.config_service import ConfigService
from src.models.data_service import DataService
from src.models.logging_service import get_logger

from .base_component import AsyncComponent

logger = get_logger(__name__)


class DataManagement(AsyncComponent):
    """
    Data management component with async background operations.
    
    Features:
    - Database statistics display
    - Async repository updates with progress tracking
    - Background indexing operations
    - Real-time status updates
    """
    
    def __init__(self, data_service: DataService, config_service: ConfigService):
        super().__init__()
        self.data_service = data_service
        self.config_service = config_service
        
        # UI state
        self.is_updating = False
        self.update_task = None
        
        # Statistics cache
        self.stats_cache = {}
    
    def create_tab(self):
        """Create the data management tab."""
        with gr.Column(elem_classes="data-container"):
            gr.Markdown("### Database Statistics")
            
            # Statistics display
            with gr.Row():
                # Left column: Database stats
                with gr.Column(scale=2):
                    self.stats_display = gr.JSON(
                        value={}, 
                        label="Database Statistics",
                        elem_classes="stats-json"
                    )
            
            # Progress display for long operations
            self.progress_text = gr.Textbox(
                label="Progress", 
                interactive=False,
                value="Ready"
            )
            
            # Buttons with async operations
            with gr.Row():
                self.update_btn = gr.Button(
                    "Update Database", 
                    variant="primary",
                    elem_classes="update-btn"
                )
                self.refresh_btn = gr.Button(
                    "Refresh Stats",
                    elem_classes="refresh-btn"
                )
                self.clear_btn = gr.Button(
                    "Clear Context",
                    elem_classes="clear-btn"
                )
            
            # Event handlers
            self._setup_event_handlers()
            
            # Auto-refresh on tab load
            self.refresh_btn.click(
                fn=self._auto_refresh_data,
                inputs=[],
                outputs=[self.progress_text, self.stats_display],
                queue=True
            )
    
    async def _auto_refresh_data(self):
        """Auto-refresh data when tab is loaded."""
        try:
            # Load database statistics
            stats = await self._get_stats_async()
            self.stats_cache = stats
            
            # Load repository information
            repo_config = await self._get_repo_config_async()
            
            return "Data loaded successfully!", stats
            
        except Exception as e:
            error_msg = f"Error loading data: {str(e)}"
            logger.error(error_msg)
            return error_msg, self.stats_cache
    
    def _load_initial_data_async(self):
        """Load initial data asynchronously when tab is created."""
        # Create a task to load initial data
        asyncio.create_task(self._load_initial_data_task())
    
    async def _load_initial_data_task(self):
        """Background task to load initial data."""
        try:
            # Load data
            stats, repo_config = await self._load_initial_data()
            
            # Update displays
            if stats:
                self.stats_cache = stats
                # Note: In Gradio, we need to trigger an update through the interface
                # This will be handled by the refresh button or when the component is ready
            
            self.progress_text.value = "Ready"
            
        except Exception as e:
            logger.error(f"Error in initial data loading: {e}")
            self.progress_text.value = f"Error loading data: {e}"
    
    def _setup_event_handlers(self):
        """Set up event handlers for the data management interface."""
        
        # Update database with progress tracking
        self.update_btn.click(
            fn=self._update_database_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True
        )
        
        # Refresh stats
        self.refresh_btn.click(
            fn=self._refresh_data_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True
        )
        
        # Clear context
        self.clear_btn.click(
            fn=self._clear_context_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True
        )
    
    async def _load_initial_data(self):
        """Load initial data for statistics and repository status."""
        try:
            # Load database statistics
            stats = await self._get_stats_async()
            self.stats_cache = stats
            
            # Load repository information
            repo_config = await self._get_repo_config_async()
            
            return stats, repo_config
            
        except Exception as e:
            error_msg = f"Error loading initial data: {str(e)}"
            logger.error(error_msg)
            return {}, {}
    
    async def _get_stats_async(self) -> dict[str, Any]:
        """Get database statistics asynchronously."""
        try:
            stats = await self.run_in_executor(self.data_service.get_context_stats)
            logger.info(f"Retrieved stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            # Return basic stats with error info
            return {
                "count": 0,
                "size_mb": 0,
                "embedding_model": "Unknown",
                "default_chunk_size": "Unknown",
                "default_chunk_overlap": "Unknown",
                "error": str(e)
            }
    
    async def _get_repo_config_async(self) -> dict[str, Any]:
        """Get repository configuration asynchronously."""
        try:
            config_service = ConfigService()
            repo_config = await self.run_in_executor(config_service.get_repositories)
            
            # Convert to dict format
            repositories = [
                {
                    "url": repo.url,
                    "branch": repo.branch,
                    "enabled": repo.enabled,
                    "file_extensions": repo.file_extensions,
                }
                for repo in repo_config
            ]
            
            return {
                "repositories": repositories,
                "total_repos": len(repositories),
                "enabled_repos": sum(1 for repo in repositories if repo["enabled"])
            }
        except Exception as e:
            logger.error(f"Error getting repo config: {e}")
            return {
                "repositories": [],
                "total_repos": 0,
                "enabled_repos": 0
            }
    
    async def _update_database_with_progress(self) -> AsyncGenerator[tuple, None]:
        """Update the knowledge base with progress tracking."""
        if self.is_updating:
            yield "Update already in progress", self.stats_cache
            return
        
        self.is_updating = True
        
        try:
            # Step 1: Load configuration
            yield "Loading configuration...", self.stats_cache
            
            config_service = ConfigService()
            repo_config = await self._get_repo_config_async()
            
            if not repo_config["repositories"]:
                yield "No repositories configured", self.stats_cache
                return
            
            enabled_repos = [repo for repo in repo_config["repositories"] if repo["enabled"]]
            
            if not enabled_repos:
                yield "No enabled repositories found", self.stats_cache
                return
            
            # Step 2: Clone repositories (Step 1/2)
            yield f"Step 1/2: Updating {len(enabled_repos)} repositories...", self.stats_cache
            
            # Convert to dict format for data service
            repo_dict = {"repositories": enabled_repos}
            
            # Run clone operation directly (it's already async)
            clone_result = await self.data_service.clone_enabled_repositories(
                repo_dict
            )
            
            if not clone_result:
                yield "Failed to update repositories", self.stats_cache
                return
            
            # Step 3: Index repositories (Step 2/2)
            yield "Step 2/2: Indexing repository content...", self.stats_cache
            
            # Run indexing operation in thread pool
            index_result = await self.run_in_executor(
                self.data_service.index_enabled_repositories,
                repo_dict
            )
            
            if index_result:
                # Get updated stats
                updated_stats = await self._get_stats_async()
                self.stats_cache = updated_stats
                
                success_msg = (f"✅ Knowledge base updated successfully! "
                              f"Indexed {updated_stats.get('count', 0)} documents "
                              f"from {len(enabled_repos)} repositories.")
                yield success_msg, updated_stats
            else:
                yield "No repositories were indexed", self.stats_cache
                
        except Exception as e:
            error_msg = f"Error updating knowledge base: {str(e)}"
            logger.error(error_msg)
            yield error_msg, self.stats_cache
            
        finally:
            self.is_updating = False
    
    async def _refresh_data(self) -> AsyncGenerator[tuple, None]:
        """Refresh the statistics and repository status display."""
        try:
            # Show refresh notification
            yield "Refreshing data...", self.stats_cache
            
            # Load database statistics
            stats = await self._get_stats_async()
            self.stats_cache = stats
            
            # Load repository information (but don't return it)
            repo_config = await self._get_repo_config_async()
            
            yield "Data refreshed successfully!", stats
            
        except Exception as e:
            error_msg = f"Error refreshing data: {str(e)}"
            logger.error(error_msg)
            yield error_msg, self.stats_cache
    
    async def _clear_context(self) -> AsyncGenerator[tuple, None]:
        """Clear the RAG context (stored documents)."""
        try:
            yield "Clearing context...", self.stats_cache
            
            # Clear context
            success = await self.run_in_executor(self.data_service.clear_context)
            
            if success:
                # Get updated stats
                updated_stats = await self._get_stats_async()
                self.stats_cache = updated_stats
                
                yield "Context cleared successfully!", updated_stats
            else:
                yield "Failed to clear context", self.stats_cache
                
        except Exception as e:
            error_msg = f"Error clearing context: {str(e)}"
            logger.error(error_msg)
            yield error_msg, self.stats_cache

    async def _update_database_wrapper(self):
        """Wrapper for async database update."""
        async for result in self._update_database_with_progress():
            yield result

    async def _refresh_data_wrapper(self):
        """Wrapper for async data refresh."""
        async for result in self._refresh_data():
            yield result

    async def _clear_context_wrapper(self):
        """Wrapper for async context clearing."""
        async for result in self._clear_context():
            yield result
    
    def _format_stats_display(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Format statistics for display."""
        formatted_stats = {
            "Total Documents": f"{stats.get('count', 0):,}",
            "Database Size": f"{stats.get('size_mb', 0):.2f} MB",
            "Embedding Model": stats.get("embedding_model", "Unknown"),
            "Chunk Size": f"{stats.get('default_chunk_size', 'Unknown')} characters",
            "Chunk Overlap": f"{stats.get('default_chunk_overlap', 'Unknown')} characters"
        }
        
        # Add error information if present
        if "error" in stats:
            formatted_stats["Status"] = f"Error: {stats['error']}"
        else:
            formatted_stats["Status"] = "Active"
        
        return formatted_stats
    
    def _format_repo_display(self, repo_config: dict[str, Any]) -> dict[str, Any]:
        """Format repository information for display."""
        repos = repo_config.get("repositories", [])
        
        repo_info = {
            "Total Repositories": repo_config.get("total_repos", 0),
            "Enabled Repositories": repo_config.get("enabled_repos", 0),
            "Repositories": []
        }
        
        for repo in repos:
            status = "Enabled" if repo.get("enabled", False) else "Disabled"
            repo_info["Repositories"].append({
                "URL": repo.get("url", ""),
                "Branch": repo.get("branch", ""),
                "Status": status,
                "Extensions": ", ".join(repo.get("file_extensions", []))
            })
        
        return repo_info
    
    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()