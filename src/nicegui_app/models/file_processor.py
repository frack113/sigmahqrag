# File Processor Service - Handles processing of different file types
import hashlib
import logging
import os
from datetime import datetime
from typing import Any


class FileProcessor:
    """
    A service to handle file processing for different formats.

    Methods:
        - process_file: Process a file based on its extension
        - process_markdown: Extract text from Markdown files
        - process_python: Extract docstrings and comments from Python files
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_file(self, file_path: str) -> str | None:
        """
        Process a file based on its extension.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[str]: Extracted text content or None if processing fails
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".md":
            return self._process_markdown(file_path)
        elif file_ext == ".py":
            return self._process_python(file_path)
        else:
            # Fallback: read as plain text
            return self._read_plain_text(file_path)

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
