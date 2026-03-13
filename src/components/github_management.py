"""
GitHub Repository Management Component

Modern GitHub repository management using Gradio's Code component for JSON editing.
Provides a clean, intuitive interface for managing multiple repositories with validation.
"""

import json
from datetime import datetime
from typing import Any

import gradio as gr
from src.models.config_service import ConfigService, RepositoryConfig
from src.models.data_service import DataService
from src.models.logging_service import get_logger

from .base_component import AsyncComponent

logger = get_logger(__name__)


class GitHubManagement(AsyncComponent):
    """
    Modern GitHub repository management component using JSON editor.

    Features:
    - JSON editor for repository configuration
    - Real-time validation with syntax highlighting
    - Template loading for quick setup
    - Comprehensive validation with clear error messages
    - All existing functionality (save, update, status display)
    """

    def __init__(self):
        super().__init__()
        self.config_service = ConfigService()
        self.data_service = DataService()

        # UI state
        self.is_updating = False
        self.current_config = {}

    def create_tab(self):
        """Create the GitHub management tab with JSON editor."""
        with gr.Column(elem_classes="github-container"):
            gr.Markdown("### 📁 GitHub Repository Management")
            gr.Markdown(
                "Edit repository configuration using JSON format. Use the template button for a quick start."
            )

            # JSON Editor
            with gr.Row():
                with gr.Column(scale=3):
                    self.json_editor = gr.Code(
                        label="Repository Configuration (JSON)",
                        value=self._get_default_json_template(),
                        language="json",
                        lines=20,
                        interactive=True,
                        show_line_numbers=True,
                    )

                with gr.Column(scale=1):
                    # Action buttons
                    with gr.Row():
                        self.load_template_btn = gr.Button(
                            "📄 Load Template", variant="secondary"
                        )

                    with gr.Row():
                        self.load_config_btn = gr.Button(
                            "📂 Load Configuration", variant="secondary"
                        )

                    with gr.Row():
                        self.validate_btn = gr.Button(
                            "✅ Validate JSON", variant="primary"
                        )

                    with gr.Row():
                        self.save_btn = gr.Button(
                            "💾 Save Configuration", variant="primary"
                        )

                    with gr.Row():
                        self.update_all_btn = gr.Button(
                            "🔄 Update All Repos", variant="secondary"
                        )

            # Validation and status
            with gr.Row():
                self.validation_status = gr.Textbox(
                    label="Validation Status",
                    interactive=False,
                    value="Ready - Edit the JSON above to get started",
                    lines=3,
                )

            # Event handlers
            self._setup_event_handlers()

            # Initialize data
            self._init_data_sync()

    def _init_data_sync(self):
        """Synchronously initialize the component with data from config."""
        try:
            # Load current configuration
            current_config = self._get_current_config_sync()
            self.current_config = current_config

            # Format as JSON string for editor
            json_string = self._format_config_for_editor(current_config)

            # Update the JSON editor directly
            if hasattr(self.json_editor, "value"):
                self.json_editor.value = json_string

            # Update validation status
            validation_msg = (
                f"Loaded {len(current_config.get('repositories', []))} repositories"
            )
            if hasattr(self.validation_status, "value"):
                self.validation_status.value = validation_msg

            logger.info(
                f"GitHub management initialized with {len(current_config.get('repositories', []))} repositories"
            )

        except Exception as e:
            error_msg = f"Error initializing data: {str(e)}"
            logger.error(error_msg)
            if hasattr(self.validation_status, "value"):
                self.validation_status.value = error_msg

    async def _load_initial_data(self):
        """Load initial data for the GitHub management component."""
        try:
            # Load current configuration
            current_config = self._get_current_config_sync()
            self.current_config = current_config

            # Format as JSON string for editor
            json_string = self._format_config_for_editor(current_config)

            return json_string, current_config

        except Exception as e:
            error_msg = f"Error loading initial data: {str(e)}"
            logger.error(error_msg)
            return self._get_default_json_template(), {}

    def _get_current_config_sync(self) -> dict[str, Any]:
        """Get current configuration synchronously."""
        try:
            # Get repositories from config service
            repo_config = self.config_service.get_repositories()

            # Convert to our JSON format
            repositories = [
                {
                    "url": repo.url,
                    "branch": repo.branch,
                    "enabled": repo.enabled,
                    "file_extensions": repo.file_extensions,
                    "description": f"Repository {i+1}",  # Add description field
                }
                for i, repo in enumerate(repo_config)
            ]

            return {
                "repositories": repositories,
                "metadata": {
                    "version": "1.0.0",
                    "last_updated": datetime.now().isoformat(),
                    "total_repos": len(repositories),
                    "enabled_repos": sum(
                        1 for repo in repositories if repo.get("enabled", True)
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error getting current config: {e}")
            return {"repositories": [], "metadata": {"version": "1.0.0"}}

    def _format_config_for_editor(self, config: dict[str, Any]) -> str:
        """Format configuration as pretty JSON string for editor."""
        try:
            return json.dumps(config, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error formatting config for editor: {e}")
            return json.dumps(
                {"repositories": [], "metadata": {"version": "1.0.0"}}, indent=2
            )

    def _get_default_json_template(self) -> str:
        """Get default JSON template for the editor."""
        template = {
            "repositories": [
                {
                    "url": "https://github.com/user/repository.git",
                    "branch": "main",
                    "enabled": True,
                    "file_extensions": ["py", "js", "ts", "html", "css"],
                    "description": "Example repository",
                }
            ],
            "metadata": {
                "version": "1.0.0",
                "description": "GitHub repository configuration for SigmaHQ RAG",
            },
        }
        return json.dumps(template, indent=2, ensure_ascii=False)

    def _get_empty_status(self) -> dict[str, Any]:
        """Get empty status summary."""
        return {
            "total_repositories": 0,
            "enabled_repositories": 0,
            "disabled_repositories": 0,
            "last_updated": "Never",
            "validation_status": "No configuration loaded",
        }

    def _setup_event_handlers(self):
        """Set up event handlers for the GitHub management interface."""

        # Load template
        self.load_template_btn.click(
            fn=self._load_template,
            inputs=[],
            outputs=[self.json_editor, self.validation_status],
            queue=True,
        )

        # Load configuration
        self.load_config_btn.click(
            fn=self._load_current_config,
            inputs=[],
            outputs=[self.json_editor, self.validation_status],
            queue=True,
        )

        # Validate JSON
        self.validate_btn.click(
            fn=self._validate_json,
            inputs=[self.json_editor],
            outputs=[self.validation_status],
            queue=True,
        )

        # Save configuration
        self.save_btn.click(
            fn=self._save_configuration,
            inputs=[self.json_editor],
            outputs=[self.validation_status],
            queue=True,
        )

        # Update all repositories
        self.update_all_btn.click(
            fn=self._update_all_repositories,
            inputs=[],
            outputs=[self.validation_status],
            queue=True,
        )

    async def _load_template(self) -> tuple:
        """Load the default JSON template."""
        try:
            template = self._get_default_json_template()
            status_msg = "Template loaded successfully"

            return template, status_msg

        except Exception as e:
            error_msg = f"Error loading template: {str(e)}"
            logger.error(error_msg)
            return self._get_default_json_template(), error_msg

    async def _load_current_config(self) -> tuple:
        """Load the current configuration from config service."""
        try:
            # Get current configuration
            current_config = self._get_current_config_sync()
            self.current_config = current_config

            # Format as JSON string for editor
            json_string = self._format_config_for_editor(current_config)

            status_msg = f"Loaded current configuration: {len(current_config.get('repositories', []))} repositories"

            return json_string, status_msg

        except Exception as e:
            error_msg = f"Error loading configuration: {str(e)}"
            logger.error(error_msg)
            return self._get_default_json_template(), error_msg

    async def _validate_json(self, json_string: str) -> str:
        """Validate JSON configuration."""
        try:
            if not json_string or not json_string.strip():
                return "❌ Error: Empty configuration"

            # Parse JSON
            config = json.loads(json_string)

            # Validate structure
            validation_result = self._validate_config_structure(config)

            if validation_result["is_valid"]:
                status_msg = f"✅ Valid configuration: {validation_result['summary']}"
            else:
                status_msg = f"❌ Validation errors: {validation_result['errors']}"

            return status_msg

        except json.JSONDecodeError as e:
            error_msg = f"❌ JSON syntax error: {str(e)}"
            return error_msg
        except Exception as e:
            error_msg = f"❌ Validation error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _validate_config_structure(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate the configuration structure."""
        errors = []

        # Check if repositories key exists
        if "repositories" not in config:
            errors.append("Missing 'repositories' key")
            return {"is_valid": False, "errors": errors, "summary": ""}

        repositories = config["repositories"]

        # Check if repositories is a list
        if not isinstance(repositories, list):
            errors.append("'repositories' must be a list")
            return {"is_valid": False, "errors": errors, "summary": ""}

        # Validate each repository
        for i, repo in enumerate(repositories):
            if not isinstance(repo, dict):
                errors.append(f"Repository {i+1} must be an object")
                continue

            # Check required fields
            if not repo.get("url"):
                errors.append(f"Repository {i+1}: URL is required")
            if not repo.get("branch"):
                errors.append(f"Repository {i+1}: Branch is required")

            # Validate enabled field
            if "enabled" in repo and not isinstance(repo["enabled"], bool):
                errors.append(f"Repository {i+1}: 'enabled' must be boolean")

            # Validate file_extensions
            if "file_extensions" in repo:
                if not isinstance(repo["file_extensions"], list):
                    errors.append(f"Repository {i+1}: 'file_extensions' must be a list")
                else:
                    for ext in repo["file_extensions"]:
                        if not isinstance(ext, str):
                            errors.append(
                                f"Repository {i+1}: file extensions must be strings"
                            )

        # Generate summary
        total_repos = len(repositories)
        enabled_repos = sum(1 for repo in repositories if repo.get("enabled", True))
        disabled_repos = total_repos - enabled_repos

        summary = (
            f"{total_repos} total, {enabled_repos} enabled, {disabled_repos} disabled"
        )

        return {
            "is_valid": len(errors) == 0,
            "errors": "; ".join(errors) if errors else "",
            "summary": summary,
        }

    async def _save_configuration(self, json_string: str) -> str:
        """Save the JSON configuration."""
        try:
            if not json_string or not json_string.strip():
                return "❌ Error: Empty configuration"

            # Parse and validate JSON
            config = json.loads(json_string)
            validation_result = self._validate_config_structure(config)

            if not validation_result["is_valid"]:
                error_msg = f"❌ Cannot save: {validation_result['errors']}"
                return error_msg

            # Convert to RepositoryConfig objects
            repositories = []
            for repo_data in config["repositories"]:
                repo_config = RepositoryConfig(
                    url=repo_data["url"],
                    branch=repo_data["branch"],
                    enabled=repo_data.get("enabled", True),
                    file_extensions=repo_data.get("file_extensions", []),
                )
                repositories.append(repo_config)

            # Save to config service
            success = await self.run_in_executor(
                self.config_service.update_repositories, repositories
            )

            if success:
                # Update current config
                self.current_config = config

                # Generate status
                status_info = self._generate_status_summary(config)
                status_msg = f"✅ Configuration saved successfully: {validation_result['summary']}"

                return status_msg
            else:
                return "❌ Error: Failed to save configuration"

        except json.JSONDecodeError as e:
            error_msg = f"❌ JSON syntax error: {str(e)}"
            return error_msg
        except Exception as e:
            error_msg = f"❌ Save error: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _update_all_repositories(self) -> str:
        """Update all enabled repositories."""
        if self.is_updating:
            return "⚠️ Update already in progress"

        self.is_updating = True

        try:
            # Get current configuration
            if not self.current_config or not self.current_config.get("repositories"):
                return "❌ No repositories configured"

            # Get enabled repositories
            enabled_repos = [
                repo
                for repo in self.current_config["repositories"]
                if repo.get("enabled", True)
            ]

            if not enabled_repos:
                return "⚠️ No enabled repositories found"

            # Update status
            status_msg = f"🔄 Updating {len(enabled_repos)} repositories..."

            # Run update operation
            update_result = await self.data_service.clone_enabled_repositories(
                {"repositories": enabled_repos}
            )

            if update_result:
                # Refresh configuration after update
                refreshed_config = self._get_current_config_sync()
                self.current_config = refreshed_config

                status_msg = f"✅ Update completed successfully: {len(enabled_repos)} repositories updated"

                return status_msg
            else:
                return "❌ Update failed"

        except Exception as e:
            error_msg = f"❌ Update error: {str(e)}"
            logger.error(error_msg)
            return error_msg

        finally:
            self.is_updating = False

    def _generate_status_summary(self, config: dict[str, Any]) -> dict[str, Any]:
        """Generate status summary from configuration."""
        repositories = config.get("repositories", [])

        total_repos = len(repositories)
        enabled_repos = sum(1 for repo in repositories if repo.get("enabled", True))
        disabled_repos = total_repos - enabled_repos

        # Get repository details
        repo_details = []
        for repo in repositories:
            repo_details.append(
                {
                    "URL": repo.get("url", "Unknown"),
                    "Branch": repo.get("branch", "Unknown"),
                    "Status": "Enabled" if repo.get("enabled", True) else "Disabled",
                    "Extensions": ", ".join(repo.get("file_extensions", [])) or "None",
                    "Description": repo.get("description", "No description"),
                }
            )

        return {
            "total_repositories": total_repos,
            "enabled_repositories": enabled_repos,
            "disabled_repositories": disabled_repos,
            "last_updated": config.get("metadata", {}).get("last_updated", "Unknown"),
            "validation_status": "Valid configuration",
            "repositories": repo_details,
        }

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
