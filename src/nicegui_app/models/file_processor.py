# File Processor Service - Handles processing of different file types
import asyncio
import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FileProcessor:
    """
    An optimized service to handle file processing for different formats.

    Features:
        - Async file processing for better UI responsiveness
        - Thread pool execution for CPU-bound operations
        - Batch processing support
        - Resource cleanup and memory management
        - Comprehensive error handling and logging
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the file processor.

        Args:
            max_workers: Maximum number of worker threads for processing
        """
        self.logger = logger
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._temp_files = []  # Track temporary files for cleanup

    async def process_file(self, file_path: str) -> Optional[str]:
        """
        Process a file based on its extension using async operations.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[str]: Extracted text content or None if processing fails
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == ".md":
                return await self._process_markdown_async(file_path)
            elif file_ext == ".py":
                return await self._process_python_async(file_path)
            elif file_ext in [".txt", ".log"]:
                return await self._read_plain_text_async(file_path)
            elif file_ext in [".pdf"]:
                return await self._process_pdf_async(file_path)
            elif file_ext in [".docx", ".doc"]:
                return await self._process_docx_async(file_path)
            else:
                # Fallback: read as plain text
                return await self._read_plain_text_async(file_path)
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return None

    async def process_files_batch(
        self, file_paths: List[str]
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Process multiple files concurrently for better performance.

        Args:
            file_paths: List of file paths to process

        Returns:
            List of tuples containing (file_path, processed_content)
        """
        if not file_paths:
            return []

        # Create tasks for concurrent processing
        tasks = [self.process_file(file_path) for file_path in file_paths]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Pair results with file paths
        processed_results = []
        for file_path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to process {file_path}: {result}")
                processed_results.append((file_path, None))
            else:
                processed_results.append((file_path, result))

        return processed_results

    async def _process_markdown_async(self, file_path: str) -> Optional[str]:
        """Process Markdown files asynchronously."""
        try:
            # Read file content in thread pool
            content = await self._read_file_async(file_path)
            if not content:
                return None

            # Process markdown in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._process_markdown_sync, content
            )
        except Exception as e:
            self.logger.error(f"Error processing Markdown file {file_path}: {e}")
            return None

    def _process_markdown_sync(self, content: str) -> Optional[str]:
        """Synchronous Markdown processing."""
        try:
            import re
            import markdown

            # Convert markdown to HTML and then extract text
            html_content = markdown.markdown(content)
            # Remove HTML tags for cleaner text
            text_content = re.sub(r"<[^>]+>", "", html_content)
            return text_content.strip()
        except Exception as e:
            self.logger.error(f"Error in synchronous Markdown processing: {e}")
            return None

    async def _process_python_async(self, file_path: str) -> Optional[str]:
        """Process Python files asynchronously."""
        try:
            # Read file content in thread pool
            content = await self._read_file_async(file_path)
            if not content:
                return None

            # Process Python file in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._process_python_sync, content
            )
        except Exception as e:
            self.logger.error(f"Error processing Python file {file_path}: {e}")
            return None

    def _process_python_sync(self, content: str) -> Optional[str]:
        """Synchronous Python file processing."""
        try:
            lines = content.split("\n")
            extracted_text = []

            for line in lines:
                # Extract comments (both inline and docstrings)
                if line.strip().startswith("#"):
                    extracted_text.append(line.strip())
                elif '"""' in line or "'''" in line:
                    # Extract docstrings
                    extracted_text.append(line.strip())

            return "\n".join(extracted_text) if extracted_text else None
        except Exception as e:
            self.logger.error(f"Error in synchronous Python processing: {e}")
            return None

    async def _process_pdf_async(self, file_path: str) -> Optional[str]:
        """Process PDF files asynchronously."""
        try:
            # Use thread pool for PDF processing (CPU and I/O intensive)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._process_pdf_sync, file_path
            )
        except Exception as e:
            self.logger.error(f"Error processing PDF file {file_path}: {e}")
            return None

    def _process_pdf_sync(self, file_path: str) -> Optional[str]:
        """Synchronous PDF processing."""
        try:
            import PyPDF2

            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text_content = []

                for page in reader.pages:
                    text_content.append(page.extract_text())

                return "\n".join(text_content) if text_content else None
        except Exception as e:
            self.logger.error(f"Error in synchronous PDF processing: {e}")
            return None

    async def _process_docx_async(self, file_path: str) -> Optional[str]:
        """Process DOCX files asynchronously."""
        try:
            # Use thread pool for DOCX processing
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._process_docx_sync, file_path
            )
        except Exception as e:
            self.logger.error(f"Error processing DOCX file {file_path}: {e}")
            return None

    def _process_docx_sync(self, file_path: str) -> Optional[str]:
        """Synchronous DOCX processing."""
        try:
            import docx

            doc = docx.Document(file_path)
            text_content = []

            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)

            return "\n".join(text_content) if text_content else None
        except Exception as e:
            self.logger.error(f"Error in synchronous DOCX processing: {e}")
            return None

    async def _read_plain_text_async(self, file_path: str) -> Optional[str]:
        """Read plain text files asynchronously."""
        try:
            return await self._read_file_async(file_path)
        except Exception as e:
            self.logger.error(f"Error reading plain text file {file_path}: {e}")
            return None

    async def _read_file_async(self, file_path: str) -> Optional[str]:
        """Read file content asynchronously using thread pool."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._read_file_sync, file_path
            )
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def _read_file_sync(self, file_path: str) -> Optional[str]:
        """Synchronous file reading."""
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def create_document_id(self, file_path: str) -> str:
        """
        Create a unique document ID from a file path.

        Args:
            file_path (str): Path to the file

        Returns:
            str: SHA256 hash of the file path
        """
        return hashlib.sha256(file_path.encode()).hexdigest()

    def create_metadata(
        self, file_path: str, repo_name: str, branch: str, repo_dir: str
    ) -> dict[str, Any]:
        """
        Create metadata dictionary for a processed file.

        Args:
            file_path (str): Path to the file
            repo_name (str): Name of the repository
            branch (str): Branch name
            repo_dir (str): Repository directory path

        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        rel_path = os.path.relpath(file_path, repo_dir)
        file_ext = os.path.splitext(file_path)[1].lower()

        return {
            "repository": repo_name,
            "branch": branch,
            "file_path": rel_path,
            "file_extension": file_ext,
            "timestamp": datetime.now().isoformat(),
        }

    def cleanup(self):
        """Clean up resources and temporary files."""
        try:
            self.executor.shutdown(wait=True)
            # Clean up any tracked temporary files
            for temp_file in self._temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp file {temp_file}: {e}")
            self._temp_files.clear()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()

    def _process_markdown(self, file_path: str) -> str | None:
        """
        Process Markdown files and extract text content.

        Args:
            file_path (str): Path to the Markdown file

        Returns:
            Optional[str]: Extracted text content or None if processing fails
        """
        try:
            import re

            import markdown

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Convert markdown to HTML and then extract text
            html_content = markdown.markdown(content)
            # Remove HTML tags for cleaner text
            text_content = re.sub(r"<[^>]+>", "", html_content)
            return text_content.strip()
        except Exception as e:
            self.logger.error(f"Error processing Markdown file {file_path}: {e}")
            return None

    def _process_python(self, file_path: str) -> str | None:
        """
        Process Python files and extract docstrings and comments.

        Args:
            file_path (str): Path to the Python file

        Returns:
            Optional[str]: Extracted text content or None if processing fails
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            extracted_text = []
            for line in lines:
                # Extract comments (both inline and docstrings)
                if line.strip().startswith("#"):
                    extracted_text.append(line.strip())
                elif '"""' in line or "'''" in line:
                    # Extract docstrings
                    extracted_text.append(line.strip())

            return "\n".join(extracted_text) if extracted_text else None
        except Exception as e:
            self.logger.error(f"Error processing Python file {file_path}: {e}")
            return None

    def _read_plain_text(self, file_path: str) -> str | None:
        """
        Read a file as plain text.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[str]: File content or None if reading fails
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

    def create_document_id(self, file_path: str) -> str:
        """
        Create a unique document ID from a file path.

        Args:
            file_path (str): Path to the file

        Returns:
            str: SHA256 hash of the file path
        """
        return hashlib.sha256(file_path.encode()).hexdigest()

    def create_metadata(
        self, file_path: str, repo_name: str, branch: str, repo_dir: str
    ) -> dict[str, Any]:
        """
        Create metadata dictionary for a processed file.

        Args:
            file_path (str): Path to the file
            repo_name (str): Name of the repository
            branch (str): Branch name
            repo_dir (str): Repository directory path

        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        rel_path = os.path.relpath(file_path, repo_dir)
        file_ext = os.path.splitext(file_path)[1].lower()

        return {
            "repository": repo_name,
            "branch": branch,
            "file_path": rel_path,
            "file_extension": file_ext,
            "timestamp": datetime.now().isoformat(),
        }
