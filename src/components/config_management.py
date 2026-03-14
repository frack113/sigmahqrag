"""
Configuration Management Component - Native Gradio Features

Uses Gradio's native features:
- gr.Textbox for configuration display/editing
- Simple event handlers with queue=True
- Real-time validation feedback
"""

import json
import logging

import gradio as gr
from src.models.config_service import ConfigService

logger = logging.getLogger(__name__)


class ConfigManagement:
    """
    Configuration management component using Gradio's native features.

    Features:
    - gr.Textbox for display/editing configuration
    - Simple click handlers (queue=True)
    - Real-time validation feedback
    """

    def __init__(self, config_service: ConfigService):
        self.config_service = config_service

    def create_tab(self) -> None:
        """Create the configuration tab with native Gradio components."""
        with gr.Column(elem_classes="config-container"):
            gr.Markdown("### ⚙️ Server Configuration")

            # Configuration display - use Textbox component (editable)
            self.config_display = gr.Textbox(
                value="",
                label="Current Configuration",
                lines=12,
                interactive=True,
                max_lines=15,
            )

            # Action buttons
            with gr.Row():
                self.load_btn = gr.Button("📂 Load Config")
                self.save_btn = gr.Button("💾 Save Config")
                self.reset_btn = gr.Button("↻ Reset to Default")

            # Status display
            self.status_text = gr.Textbox(
                label="Status", interactive=False, value="Ready"
            )

            # Event handlers
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers using Gradio's native pattern."""

        self.load_btn.click(
            fn=self._load_config,
            inputs=[],
            outputs=[self.config_display, self.status_text],
            queue=True,
        )

        self.save_btn.click(
            fn=self._save_config,
            inputs=[self.config_display],
            outputs=[self.status_text],
            queue=True,
        )

        self.reset_btn.click(
            fn=self._reset_config,
            inputs=[],
            outputs=[self.config_display, self.status_text],
            queue=True,
        )

    def _load_config(self) -> tuple[str, str]:
        """Load current configuration."""
        try:
            from src.shared.config_manager import ConfigManager, create_config_manager
            
            # Create fresh config manager to get latest values
            config_mgr = create_config_manager()
            config = config_mgr.get_config_for_ui()

            # Format as JSON string for display
            config_json = json.dumps(config, indent=2)

            return config_json, "✅ Configuration loaded"

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return f"❌ Error: {str(e)}", "Failed to load configuration"

    def _save_config(self, json_string: str) -> str:
        """Save configuration from JSON string."""
        try:
            # Parse and validate JSON first
            parsed = self._parse_json(json_string)

            if parsed is None:
                return "❌ Invalid JSON format"

            # Update configuration via config manager
            result = self.config_service.config_manager.update_config(parsed)

            if result:
                return "✅ Configuration saved successfully"
            else:
                return "❌ Failed to save configuration"

        except json.JSONDecodeError as e:
            return f"❌ Invalid JSON syntax: {str(e)}"
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return f"❌ Error: {str(e)}"

    def _parse_json(self, json_string: str) -> dict | None:
        """Parse and validate JSON configuration."""
        if not json_string or not json_string.strip():
            return None

        try:
            parsed = json.loads(json_string)

            # Validate required fields based on config structure
            errors = []
            
            if "network" not in parsed:
                errors.append("Missing 'network' section")
            else:
                network_config = parsed["network"]
                
                for field in ["ip", "port"]:
                    if field not in network_config:
                        errors.append(f"Missing '{field}' in network config")

            if "llm" not in parsed:
                errors.append("Missing 'llm' section")
            else:
                llm_config = parsed["llm"]
                for field in ["model", "base_url", "temperature", "max_tokens"]:
                    if field not in llm_config:
                        errors.append(f"Missing '{field}' in llm config")

            if "ui_css" not in parsed:
                errors.append("Missing 'ui_css' section")

            if "repositories" not in parsed:
                errors.append("Missing 'repositories' section")

            if errors:
                return None

            return parsed

        except json.JSONDecodeError:
            return None

    def _reset_config(self) -> tuple[str, str]:
        """Reset to default configuration."""
        try:
            import json

            # Build a minimal valid config for reset
            default_config = {
                "network": {
                    "ip": "127.0.0.1",
                    "port": 8000
                },
                "llm": {
                    "model": "qwen/qwen3.5-9b",
                    "temperature": 0.7,
                    "max_tokens": 5000,
                    "base_url": "http://127.0.0.1:1234"
                },
                "repositories": [],
                "ui_css": {
                    "theme": "soft",
                    "title": "SigmaHQ RAG"
                }
            }
            
            config_json = json.dumps(default_config, indent=2)

            return config_json, "✅ Configuration reset to defaults"

        except Exception as e:
            logger.error(f"Error resetting config: {e}")
            return "", f"❌ Error: {str(e)}"

    def cleanup(self):
        """Clean up resources."""
        pass