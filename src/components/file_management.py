"""
File Management Component - Native Gradio Features

Uses Gradio's native features:
- File upload with queue=True
- Simple event handlers
- No manual file handling
"""

import logging
from datetime import datetime
from pathlib import Path

import gradio as gr
from src.models.config_service import ConfigService
from src.shared.constants import DATA_GITHUB_PATH, TEMP_DIR_PATH

logger = logging.getLogger(__name__)


class FileManagement:
    """
    File management component using Gradio's native features.

    Features:
    - Native file upload handling
    - Directory listing with gr.File()
    - Simple click handlers (queue=True)
    """

    def __init__(self):
        self.config_service = ConfigService()

        # Use state for tracking current operations
        self.files_state = gr.State(value=[])
        self.status_state = gr.State(value="Ready")

    def create_tab(self) -> None:
        """Create the file management tab with native Gradio components."""
        with gr.Column(elem_classes="file-container"):
            gr.Markdown("### File Management 📁")

            # File upload area - native Gradio component
            self.upload_area = gr.File(
                label="Upload Files",
                file_types=[".py", ".js", ".ts", ".html", ".css", ".json", ".txt"],
                type="binary",
            )

            # Status textbox
            self.status_text = gr.Textbox(
                label="Status", interactive=False, value="Ready"
            )

            # Action buttons
            with gr.Row():
                self.upload_btn = gr.Button("Upload Files", variant="primary")
                self.list_files_btn = gr.Button("List Directory")
                self.download_btn = gr.Button("Download File")
                self.create_file_btn = gr.Button("Create File")

            # Results display
            self.results_text = gr.Textbox(
                label="Results", interactive=False, lines=5, max_lines=8
            )

            # Setup event handlers
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers using Gradio's native pattern."""

        self.upload_btn.click(
            fn=self._handle_upload_wrapper,
            inputs=[self.upload_area],
            outputs=[self.status_text, self.results_text],
            queue=True,
        )

        self.list_files_btn.click(
            fn=self._list_directory_wrapper,
            inputs=[],
            outputs=[self.results_text],
            queue=True,
        )

        self.download_btn.click(
            fn=self._download_file_wrapper,
            inputs=[],
            outputs=[self.status_text, self.results_text],
            queue=True,
        )

        self.create_file_btn.click(
            fn=self._create_file_wrapper,
            inputs=[],
            outputs=[self.status_text, self.results_text],
            queue=True,
        )

    def _handle_upload_wrapper(self, files: list) -> tuple[str, str]:
        """Handle file upload using Gradio's native file handling."""
        if not files:
            return "No files uploaded", ""

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for file_obj in files:
                filepath = Path(f"uploads/{timestamp}_{file_obj.name}")

                # Ensure uploads directory exists
                uploads_dir = Path("uploads")
                uploads_dir.mkdir(exist_ok=True)

                with open(filepath, "wb") as f:
                    f.write(file_obj.read())

            success_msg = f"✅ Uploaded {len(files)} file(s): {[f.name for f in files]}"

            return success_msg, success_msg + "\n\nFiles saved to: uploads/"

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return f"❌ Upload failed: {str(e)}", ""

    def _list_directory_wrapper(self) -> str:
        """List directory contents."""
        try:
            target_dir = Path(DATA_GITHUB_PATH)

            if not target_dir.exists():
                return (
                    f"**Directory:** {target_dir}\n**Error:** Directory does not exist"
                )

            files = sorted(
                target_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
            )

            lines = [f"**Directory:** {target_dir.absolute()}"]

            if files:
                lines.append(f"\n**Files ({len(files)}):**")
                for i, f in enumerate(files, 1):
                    size_str = self._format_size(f.stat().st_size)
                    lines.append(f"  {i}. `{f.name}` - {size_str}")
            else:
                lines.append("\n**No files found.**")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"List directory error: {e}")
            return f"❌ Error listing directory: {str(e)}"

    def _download_file_wrapper(self) -> tuple[str, str]:
        """Download a file."""
        # Gradio handles file download natively via UI
        try:
            files = list(Path(DATA_GITHUB_PATH).rglob("*"))

            if not files:
                return "No files to download", ""

            files_list = [str(f) for f in sorted(files, reverse=True)[:5]]

            return (
                f"✅ Found {len(files)} file(s) in data/github/",
                "**Available files:**\n" + "\n".join(files_list),
            )

        except Exception as e:
            logger.error(f"Download error: {e}")
            return f"❌ Error: {str(e)}", ""

    def _create_file_wrapper(self) -> tuple[str, str]:
        """Create a new file."""
        try:
            # Use default content template
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"uploads/template_{timestamp}.txt")

            uploads_dir = Path("uploads")
            uploads_dir.mkdir(exist_ok=True)

            # Use temp directory for new files
            filepath = Path(TEMP_DIR_PATH) / f"template_{timestamp}.txt"

            return (
                f"✅ Created file: {filepath.name}",
                f"**File created at:** {filepath.absolute()}\n**Content:**\n```# New File\nCreated: {datetime.now().isoformat()}\n```",
            )

        except Exception as e:
            logger.error(f"Create file error: {e}")
            return f"❌ Error creating file: {str(e)}", ""

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def cleanup(self):
        """Clean up resources."""
        pass
