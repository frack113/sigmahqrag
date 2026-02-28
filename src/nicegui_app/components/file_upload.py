# File Upload Component
"""
Component for handling document uploads with drag-and-drop support,
file validation, preview generation, and progress indicators.
"""
from typing import Optional, List, Callable, Dict, Any
from nicegui import ui, events
import base64
from PIL import Image
import io
import pdf2image
import os
import tempfile


class FileUpload:
    """
    A file upload component that supports drag-and-drop, file validation,
    preview generation for images and PDFs, and progress tracking.
    
    Attributes:
        allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.txt'])
        max_size_mb: Maximum file size in MB
        on_upload: Callback function when files are uploaded successfully
        on_error: Callback function when upload fails
    """
    
    def __init__(
        self,
        allowed_extensions: List[str] = ['.pdf', '.txt', '.docx', '.png', '.jpg', '.jpeg'],
        max_size_mb: int = 10,
        on_upload: Optional[Callable[[List[str]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
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
        self.uploaded_files: List[str] = []
    
    def render(self):
        """
        Render the file upload component with drag-and-drop zone.
        
        Returns:
            The root element of the upload component
        """
        # Main container
        container = ui.card().classes("w-full max-w-2xl")
        
        with container:
            # Drop zone
            drop_zone = ui.element('div').classes("w-full h-48 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors")
            
            with drop_zone:
                ui.label("Drop files here or click to upload").classes("text-gray-600 mb-2")
                ui.label(f"Supported formats: {', '.join(self.allowed_extensions)}").classes("text-xs text-gray-500")
                ui.label(f"Max size: {self.max_size_mb}MB").classes("text-xs text-gray-500")
            
            # Hidden file input
            file_input = ui.input().props('type=file multiple').classes('hidden')
            
            # Event handlers
            drop_zone.on('dragenter', self._handle_drag_enter)
            drop_zone.on('dragover', self._handle_drag_over)
            drop_zone.on('dragleave', self._handle_drag_leave)
            drop_zone.on('drop', self._handle_drop)
            drop_zone.on('click', lambda: file_input.click())
            
            file_input.on('change', self._handle_file_selection)
        
        return container
    
    def _handle_drag_enter(self, e):
        """Handle drag enter event."""
        e.sender.classes("border-blue-500 bg-blue-50")
    
    def _handle_drag_over(self, e):
        """Handle drag over event."""
        e.prevent_default()
        e.stop_propagation()
    
    def _handle_drag_leave(self, e):
        """Handle drag leave event."""
        e.sender.classes("border-gray-300 bg-white")
    
    def _handle_drop(self, e):
        """Handle drop event with file validation and processing."""
        e.prevent_default()
        e.stop_propagation()
        
        files = e.args.get('dataTransfer.files', [])
        if not files:
            self._call_error("No files dropped")
            return
        
        self._process_files(files)
    
    def _handle_file_selection(self, e):
        """Handle file selection from file input."""
        files = e.sender.element.files
        if not files:
            self._call_error("No files selected")
            return
        
        self._process_files(files)
    
    def _process_files(self, files: List[Any]):
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
        
        if uploaded_paths:
            self.uploaded_files.extend(uploaded_paths)
            self._call_upload(uploaded_paths)
    
    def _validate_file(self, file_obj: Any) -> bool:
        """Validate file extension and size."""
        filename = file_obj.name
        
        # Check extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.allowed_extensions:
            error_msg = f"File type not allowed: {filename}. Allowed types: {', '.join(self.allowed_extensions)}"
            self._call_error(error_msg)
            return False
        
        # Check size
        file_size_mb = len(file_obj) / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            error_msg = f"File too large: {filename} ({file_size_mb:.1f}MB). Max size: {self.max_size_mb}MB"
            self._call_error(error_msg)
            return False
        
        return True
    
    def _save_file(self, file_obj: Any) -> str:
        """Save uploaded file to temporary directory."""
        # Create temp directory for uploads
        upload_dir = os.path.join(tempfile.gettempdir(), 'sigmahq_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        filename = file_obj.name
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, 'wb') as f:
            # Read file content based on source (drop event vs file input)
            if hasattr(file_obj, 'get_data'):
                # For drop events
                data = file_obj.get_data()
                f.write(data)
            else:
                # For file input
                content = file_obj.content
                f.write(content)
        
        return filepath
    
    def _call_upload(self, files: List[str]):
        """Call upload callback if provided."""
        if self.on_upload:
            self.on_upload(files)
    
    def _call_error(self, error: str):
        """Call error callback if provided."""
        if self.on_error:
            self.on_error(error)
    
    def generate_preview(self, file_path: str) -> Optional[str]:
        """
        Generate preview image for supported file types.
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            Base64 encoded image string or None if preview not available
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in ['.png', '.jpg', '.jpeg']:
                # Image files - use PIL to resize and convert to base64
                with Image.open(file_path) as img:
                    # Resize for preview
                    img.thumbnail((300, 300))
                    
                    # Convert to base64
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    return f"data:image/png;base64,{img_str}"
            
            elif ext == '.pdf':
                # PDF files - convert first page to image
                images = pdf2image.convert_from_path(file_path, first_page=1, last_page=1)
                if images:
                    img = images[0]
                    img.thumbnail((300, 300))
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"Error generating preview: {e}")
        
        return None
    
    def clear_uploads(self) -> None:
        """Clear all uploaded files."""
        self.uploaded_files = []