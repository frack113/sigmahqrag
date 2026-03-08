# File Upload Component
"""
Simplified file upload component for NiceGUI 3.x compatibility.
Uses built-in NiceGUI file input with validation and preview generation.
"""

import base64
import io
import os
import tempfile
from collections.abc import Callable
from typing import Any

from nicegui import ui
from PIL import Image


class FileUpload:
    """
    A simplified file upload component that supports file validation,
    preview generation for images, and progress tracking.

    Attributes:
        allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.txt'])
        max_size_mb: Maximum file size in MB
        on_upload: Callback function when files are uploaded successfully
        on_error: Callback function when upload fails
    """

    def __init__(
        self,
        allowed_extensions: list[str] = [
            ".pdf",
            ".txt",
            ".docx",
            ".png",
            ".jpg",
            ".jpeg",
        ],
        max_size_mb: int = 10,
        on_upload: Callable[[list[str]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        """
        Initialize the file upload component.

        Args:
            allowed_extensions: List of allowed file extensions
            max_size_mb: Maximum file size in MB (default: 10)
            on_upload: Callback for successful uploads (receives list of file paths)
            on_error: Callback for errors (receives error message)
        """
        self.allowed_extensions = allowed_extensions
        self.max_size_mb = max_size_mb
        self.on_upload = on_upload
        self.on_error = on_error
        self.uploaded_files: list[str] = []

    def render(self):
        """
        Render the file upload component with NiceGUI 3.x compatible elements.

        Returns:
            The root element of the upload component
        """
        # Main container
        container = ui.card().classes("w-full")

        with container:
            # Button row with [+] button and file count
            with ui.row().classes("w-full mb-2 gap-2"):
                # [+] button
                ui.button(
                    icon="add",
                    text="Add Files",
                    on_click=self._trigger_file_input,
                ).classes("bg-blue-600 text-white hover:bg-blue-700")

                # File count display
                file_count_text = f"{len(self.uploaded_files)} file(s) uploaded"
                self.file_count = ui.label(file_count_text)
                self.file_count.classes("text-sm text-gray-600")

            # File input using NiceGUI's built-in component
            self.file_input = (
                ui.input(placeholder="Select files...")
                .props("type=file multiple accept='*/*'")
                .classes("hidden")
            )

            # Upload area with clear instructions
            with ui.column().classes("w-full items-center gap-2"):
                ui.label("Click 'Add Files' or drag and drop files here").classes(
                    "text-gray-600 mb-2"
                )
                ui.label(
                    f"Supported formats: {', '.join(self.allowed_extensions)}"
                ).classes("text-xs text-gray-500")
                ui.label(f"Max size: {self.max_size_mb}MB").classes(
                    "text-xs text-gray-500"
                )

            # Event handlers using NiceGUI 3.x patterns
            self.file_input.on("change", self._handle_file_selection)

        return container

    def _trigger_file_input(self):
        """Trigger the file input to open."""
        self.file_input.run_method("click")

    def _handle_file_selection(self, e):
        """Handle file selection from file input."""
        files = e.args
        if not files:
            self._call_error("No files selected")
            return

        self._process_files(files)

    def _process_files(self, files: list[Any]):
        """Process uploaded files with validation and preview generation."""
        uploaded_paths = []

        for file_obj in files:
            try:
                # Validate file
                if not self._validate_file(file_obj):
                    continue

                # Save file temporarily
                file_path = self._save_file(file_obj)
                uploaded_paths.append(file_path)

            except Exception as ex:
                error_msg = f"Error processing file: {str(ex)}"
                self._call_error(error_msg)
                continue  # Continue with next file instead of stopping

        if uploaded_paths:
            self.uploaded_files.extend(uploaded_paths)
            self._call_upload(uploaded_paths)
            self._update_file_count()
        elif not files:  # No valid files were processed
            self._call_error("No valid files were uploaded")

    def _validate_file(self, file_obj: Any) -> bool:
        """Validate file extension and size."""
        filename = file_obj["name"]

        # Check extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.allowed_extensions:
            allowed_types = ", ".join(self.allowed_extensions)
            error_msg = (
                f"File type not allowed: {filename}. Allowed types: {allowed_types}"
            )
            self._call_error(error_msg)
            return False

        # Check size
        file_size_mb = file_obj["size"] / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            error_msg = (
                f"File too large: {filename} ({file_size_mb:.1f}MB). "
                f"Max size: {self.max_size_mb}MB"
            )
            self._call_error(error_msg)
            return False

        return True

    def _save_file(self, file_obj: Any) -> str:
        """Save uploaded file to temporary directory."""
        # Create temp directory for uploads
        upload_dir = os.path.join(tempfile.gettempdir(), "sigmahq_uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # Save file with unique name to prevent collisions
        filename = file_obj["name"]
        ext = os.path.splitext(filename)[1].lower()
        import uuid

        unique_filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, unique_filename)

        try:
            # Get file content from NiceGUI's file object
            content = file_obj["content"]
            with open(filepath, "wb") as f:
                f.write(content)
        except Exception as e:
            # Clean up if save fails
            if os.path.exists(filepath):
                os.remove(filepath)
            raise Exception(f"Failed to save file: {str(e)}")

        return filepath

    def _call_upload(self, files: list[str]):
        """Call upload callback if provided."""
        if self.on_upload:
            self.on_upload(files)

    def _call_error(self, error: str):
        """Call error callback if provided."""
        if self.on_error:
            self.on_error(error)

    def generate_preview(self, file_path: str) -> str | None:
        """
        Generate preview image for supported file types.

        Args:
            file_path: Path to the uploaded file

        Returns:
            Base64 encoded image string or None if preview not available
        """
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext in [".png", ".jpg", ".jpeg"]:
                # Image files - use PIL to resize and convert to base64
                with Image.open(file_path) as img:
                    # Resize for preview
                    img.thumbnail((300, 300))

                    # Convert to base64
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    return f"data:image/png;base64,{img_str}"

            elif ext == ".pdf":
                # PDF files - use text-only mode (no preview generation)
                # This simplifies the implementation and removes pdf2image dependency
                return None

        except Exception as e:
            print(f"Error generating preview: {e}")

        return None

    def _update_file_count(self):
        """Update the file count display."""
        if hasattr(self, "file_count"):
            self.file_count.set_text(f"{len(self.uploaded_files)} file(s) uploaded")

    def clear_uploads(self) -> None:
        """Clear all uploaded files."""
        self.uploaded_files = []
        self._update_file_count()
