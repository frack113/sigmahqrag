"""
GitHub Repository Management Component - Native Gradio Features

Uses Gradio's native features:
- gr.Code for JSON editing (syntax highlighting)
- Simple click handlers with queue=True
- No manual event loop management
"""

import json
import logging
from typing import Any

import gradio as gr
from src.models.config_service import ConfigService, RepositoryConfig

logger = logging.getLogger(__name__)


class GitHubManagement:
    """
    GitHub repository management using Gradio's native JSON editor.

    Features:
    - Syntax-highlighted JSON editing
    - Real-time validation
    - Simple click handlers (queue=True for async)
    """

    def __init__(self):
        self.config_service = ConfigService()
        self.current_config: dict[str, Any] | None = None

        # Use Gradio state for UI state management
        self.json_state = gr.State(
            value=json.dumps(self._get_default_template(), indent=2)
        )
        self.status_state = gr.State(value="Ready - Edit the JSON above to get started")

    def create_tab(self) -> None:
        """Create the GitHub management tab with native Gradio components."""
        with gr.Column(elem_classes="github-container"):
            gr.Markdown("### 📁 GitHub Repository Management")
            gr.Markdown(
                "Edit repository configuration using JSON format. "
                "Use the template button for a quick start."
            )

            # JSON Editor - Gradio's native code component with syntax highlighting
            self.json_editor = gr.Code(
                label="Repository Configuration (JSON)",
                language="json",
                lines=20,
                interactive=True,
                show_line_numbers=True,
            )

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
                self.validate_btn = gr.Button("✅ Validate JSON", variant="primary")

            with gr.Row():
                self.save_btn = gr.Button("💾 Save Configuration", variant="primary")

            with gr.Row():
                self.update_all_btn = gr.Button(
                    "🔄 Update All Repos", variant="secondary"
                )

            # Status display
            self.validation_status = gr.Textbox(
                label="Validation Status",
                interactive=False,
                lines=3,
            )

            # Event handlers - all use queue=True for async support
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers using Gradio's native pattern."""

        self.load_template_btn.click(
            fn=self._load_template, inputs=[], outputs=[self.json_editor], queue=True
        )

        self.load_config_btn.click(
            fn=self._load_current_config,
            inputs=[],
            outputs=[self.json_editor],
            queue=True,
        )

        self.validate_btn.click(
            fn=self._validate_json,
            inputs=[self.json_editor],
            outputs=[self.validation_status],
            queue=True,
        )

        self.save_btn.click(
            fn=self._save_configuration,
            inputs=[self.json_editor],
            outputs=[self.validation_status],
            queue=True,
        )

        self.update_all_btn.click(
            fn=self._update_all_repositories,
            inputs=[],
            outputs=[self.validation_status],
            queue=True,
        )

    def _load_template(self) -> str:
        """Load the default JSON template."""
        return json.dumps(self._get_default_template(), indent=2)

    def _load_current_config(self) -> str | None:
        """Load current configuration from config service."""
        try:
            repo_config = self.config_service.get_repositories()

            repositories = [
                {
                    "url": repo.url,
                    "branch": repo.branch,
                    "enabled": repo.enabled,
                    "file_extensions": repo.file_extensions,
                }
                for repo in repo_config
            ]

            config = {
                "repositories": repositories,
                "metadata": {
                    "version": "1.0.0",
                    "total_repos": len(repositories),
                    "enabled_repos": sum(1 for repo in repositories if repo["enabled"]),
                },
            }

            self.current_config = config
            return json.dumps(config, indent=2)

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return None

    def _validate_json(self, json_string: str) -> str:
        """Validate JSON configuration."""
        if not json_string or not json_string.strip():
            return "❌ Error: Empty configuration"

        try:
            # Parse JSON
            config = json.loads(json_string)

            # Validate structure
            validation_result = self._validate_config_structure(config)

            if validation_result["is_valid"]:
                return f"✅ Valid configuration: {validation_result['summary']}"
            else:
                return f"❌ Validation errors: {validation_result['errors']}"

        except json.JSONDecodeError as e:
            return f"❌ JSON syntax error: {str(e)}"
        except Exception as e:
            return f"❌ Validation error: {str(e)}"

    def _validate_config_structure(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate the configuration structure."""
        errors = []

        if "repositories" not in config:
            errors.append("Missing 'repositories' key")
            return {"is_valid": False, "errors": "; ".join(errors), "summary": ""}

        repositories = config["repositories"]

        if not isinstance(repositories, list):
            errors.append("'repositories' must be a list")
            return {"is_valid": False, "errors": "; ".join(errors), "summary": ""}

        # Validate each repository
        for i, repo in enumerate(repositories):
            if not isinstance(repo, dict):
                errors.append(f"Repository {i+1} must be an object")
                continue

            if not repo.get("url"):
                errors.append(f"Repository {i+1}: URL is required")
            if not repo.get("branch"):
                errors.append(f"Repository {i+1}: Branch is required")

        total_repos = len(repositories)
        enabled_repos = sum(1 for repo in repositories if repo.get("enabled", True))

        return {
            "is_valid": len(errors) == 0,
            "errors": "; ".join(errors),
            "summary": f"{total_repos} total, {enabled_repos} enabled, {total_repos - enabled_repos} disabled",
        }

    def _save_configuration(self, json_string: str) -> str:
        """Save the JSON configuration."""
        if not json_string or not json_string.strip():
            return "❌ Error: Empty configuration"

        try:
            config = json.loads(json_string)
            validation_result = self._validate_config_structure(config)

            if not validation_result["is_valid"]:
                return f"❌ Cannot save: {validation_result['errors']}"

            # Convert to RepositoryConfig objects
            repositories = [
                RepositoryConfig(
                    url=repo_data["url"],
                    branch=repo_data["branch"],
                    enabled=repo_data.get("enabled", True),
                    file_extensions=repo_data.get("file_extensions", []),
                )
                for repo_data in config["repositories"]
            ]

            # Save to config service (synchronous method)
            result = self.config_service.update_repositories(repositories)

            if result:
                self.current_config = config
                return "✅ Configuration saved successfully"
            else:
                return "❌ Error: Failed to save configuration"

        except json.JSONDecodeError as e:
            return f"❌ JSON syntax error: {str(e)}"
        except Exception as e:
            return f"❌ Save error: {str(e)}"

    def _update_all_repositories(self) -> str:
        """Update all enabled repositories."""
        if not self.current_config or not self.current_config.get("repositories"):
            return "❌ No repositories configured"

        enabled_repos = [
            repo
            for repo in self.current_config["repositories"]
            if repo.get("enabled", True)
        ]

        if not enabled_repos:
            return "⚠️ No enabled repositories found"

        try:
            update_result = self.config_service.clone_enabled_repositories(
                {"repositories": enabled_repos}
            )

            if update_result:
                return f"✅ Update completed successfully: {len(enabled_repos)} repositories updated"
            else:
                return "❌ Update failed"

        except Exception as e:
            return f"❌ Update error: {str(e)}"

    def _get_default_template(self) -> dict[str, Any]:
        """Get default JSON template for the editor."""
        return {
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

    def cleanup(self):
        """Clean up resources."""
        pass
