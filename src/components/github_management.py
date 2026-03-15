"""
GitHub Repository Management Component - Native Gradio Features

Uses Gradio's native features:
- gr.Code for JSON editing (syntax highlighting)
- Simple click handlers with queue=True
- No manual event loop management
"""

import json
import logging
from typing import TYPE_CHECKING, Any

import gradio as gr
import requests
from src.models.config_service import RepositoryConfig

if TYPE_CHECKING:
    from src.models.config_service import ConfigService


logger = logging.getLogger(__name__)


class GitHubManagement:
    """
    GitHub repository management using Gradio's native JSON editor.

    Features:
    - Syntax-highlighted JSON editing
    - Real-time validation
    - Simple click handlers (queue=True for async)
    - SigmaHQ repository auto-add from GitHub API
    """

    def __init__(self) -> None:
        # Lazy-load ConfigService when first needed to avoid initialization errors
        from src.models.config_service import ConfigService

        self._config_service: ConfigService | None = None
        self.current_config: dict[str, Any] | None = None

        # Use Gradio state for UI state management - always start with template
        self.json_state = gr.State(
            value=json.dumps(self._get_default_template(), indent=2)
        )
        self.status_state = gr.State(value="Ready - Edit the JSON above to get started")

        # Load config on first use (lazy initialization)
        try:
            from src.models.config_service import ConfigService

            self.config_service = ConfigService()
        except Exception as e:
            logger.error(f"Failed to initialize ConfigService: {e}")

    def create_tab(self) -> None:
        """Create the GitHub management tab using native Gradio features."""
        with gr.Column(variant="compact"):  # Native compact variant = less padding
            gr.Markdown("### 📁 GitHub Repository Management")
            gr.Markdown(
                "Edit repository configuration using JSON format. "
                "**💡 Quick tips:** Click to edit • `Ctrl+Enter` to format"
            )

            # Use native Gradio Row with scale parameter (no CSS needed)
            with gr.Row(
                equal_height=False
            ):  # Native equal_height=False = no vertical scrollbar on empty rows
                # Left: JSON editor column with native scrolling
                with gr.Column(scale=2, min_width=500):
                    self.json_editor = gr.Code(
                        value=json.dumps(self._get_default_template(), indent=2),
                        language="json",
                        lines=12,
                        interactive=True,
                        show_line_numbers=False,
                    )

                # Right: Buttons column - wider to fit button text (min_width=160)
                with gr.Column(scale=0, min_width=160):
                    self.load_template_btn = gr.Button(
                        "📄 Load Template", variant="secondary"
                    )
                    self.load_config_btn = gr.Button(
                        "📂 Load Configuration", variant="secondary"
                    )
                    self.validate_btn = gr.Button("✅ Validate JSON", variant="primary")
                    self.save_btn = gr.Button(
                        "💾 Save Configuration", variant="primary"
                    )
                    self.update_all_btn = gr.Button(
                        "🔄 Update All Repos", variant="secondary"
                    )
                    self.sigmahq_btn = gr.Button(
                        "🔍 Add SigmaHQ Repos", variant="secondary"
                    )

            # Status textbox using native compact styling
            self.validation_status = gr.Textbox(
                label="",
                value="Ready - Edit the JSON above to get started",
                interactive=False,
                lines=2,
                container=False,
            )

            self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
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

        self.sigmahq_btn.click(
            fn=self._add_sigmahq_repos,
            inputs=[self.json_editor],
            outputs=[self.json_editor, self.validation_status],
            queue=True,
        )

    def _load_template(self) -> str:
        """Load the default JSON template."""
        return json.dumps(self._get_default_template(), indent=2)

    def _load_current_config(self) -> str:
        """Load current configuration from data/config.json.

        Returns template if config service unavailable to prevent Gradio API test errors.
        Always returns valid JSON string, never None."""
        # Always return a valid JSON string - Gradio tests all handlers on init
        try:
            # Lazy initialize config service
            if self._config_service is None:
                self._config_service = ConfigService()

            # Get repositories data from config service (lazy init ensures file exists)
            repos_data = self.config_service.get_repositories()

            repositories = [
                {
                    "url": repo.url,
                    "branch": repo.branch,
                    "enabled": repo.enabled,
                    "file_extensions": list(repo.file_extensions),
                }
                for repo in repos_data
            ]

            config = {
                "repositories": repositories,
                "metadata": {
                    "version": "1.0.0",
                    "total_repos": len(repositories),
                    "enabled_repos": sum(
                        1 for repo in repositories if repo.get("enabled")
                    ),
                },
            }

            self.current_config = config
            return json.dumps(config, indent=2)

        except KeyError:
            # Config file missing required keys - fall back to template
            logger.error("Config file has missing or invalid structure")
            return json.dumps(self._get_default_template(), indent=2)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Always return template on error - NEVER return None
            # This prevents Gradio API test failures
            return json.dumps(self._get_default_template(), indent=2)

    def _fetch_sigmahq_repos(self) -> list[dict] | None:
        """Fetch up to 100 SigmaHQ repos from GitHub API (public + org members)."""
        try:
            # Use query parameter 'per_page=100' for max results in single request
            url = "https://api.github.com/orgs/SigmaHQ/repos"
            params = {
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            repos: list[dict] = []
            for repo_data in response.json():
                # Extract key info from API response
                repos.append(
                    {
                        "name": repo_data["name"],
                        "full_name": repo_data["full_name"],
                        "html_url": repo_data["html_url"],
                        "default_branch": repo_data.get("default_branch", "main"),
                        "description": repo_data.get("description", ""),
                    }
                )

            logger.info(f"Fetched {len(repos)} SigmaHQ repositories from GitHub API")
            return repos if repos else None

        except requests.RequestException as e:
            logger.error(f"Failed to fetch SigmaHQ repos: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching SigmaHQ repos: {e}")
            return None

    def _add_sigmahq_repos(self, json_string: str) -> tuple[str, str]:
        """Add missing SigmaHQ repositories to the configuration.

        Returns tuple of (updated_json_string, status_message)."""
        if not json_string or not json_string.strip():
            return (json_string, "❌ Error: Empty configuration")

        try:
            # Parse current config
            config = json.loads(json_string)

            if "repositories" not in config:
                return (
                    json_string,
                    "❌ Cannot add SigmaHQ repos: missing 'repositories' key",
                )

            # Get list of already existing repo URLs (to avoid duplicates)
            existing_urls = {r["url"] for r in config["repositories"] if r.get("url")}

            # Fetch new repos from API
            sigmahq_repos = self._fetch_sigmahq_repos()

            if not sigmahq_repos:
                return (
                    json_string,
                    "⚠️ Could not fetch SigmaHQ repos from GitHub API (check network)",
                )

            # Add only the missing repos that aren't already in config
            added_count = 0
            for api_repo in sigmahq_repos:
                repo_url = f"{api_repo['html_url']}.git"
                if repo_url not in existing_urls:
                    config["repositories"].append(
                        {
                            "url": repo_url,
                            "branch": api_repo.get("default_branch", "main"),
                            "enabled": False,  # Disabled by default
                            "file_extensions": [],  # Empty array = use defaults
                            "description": api_repo.get("description", ""),
                        }
                    )
                    added_count += 1

            result_message = (
                f"✅ Added {added_count} SigmaHQ repos. Click Save Config to persist."
            )

            if added_count > 0:
                return (json.dumps(config, indent=2), result_message)
            elif not existing_urls:
                return (
                    json_string,
                    "ℹ️ No new SigmaHQ repos to add (already in config)",
                )
            else:
                return (json.dumps(config, indent=2), result_message)

        except json.JSONDecodeError as e:
            return (json_string, f"❌ JSON syntax error: {str(e)}")
        except Exception as e:
            return (json_string, f"❌ Error adding SigmaHQ repos: {str(e)}")

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

    def _validate_config_structure(self, config: dict[str, Any]) -> dict[str, str]:
        """Validate the configuration structure."""
        errors: list[str] = []

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
            "summary": (
                f"{total_repos} repos total. "
                f"{enabled_repos} enabled, {total_repos - enabled_repos} disabled"
            ),
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

            # Initialize config_service lazily (needed for handler tests)
            if self._config_service is None:
                self._config_service = ConfigService()

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

            success_msg = f"✅ Update completed. {len(enabled_repos)} repos updated."
            if update_result:
                return success_msg
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

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
