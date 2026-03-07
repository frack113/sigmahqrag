# File Processor Service - Handles processing of different file types
import logging
from typing import Optional, Dict, Any
import os
import hashlib
from datetime import datetime


class FileProcessor:
    """
    A service to handle file processing for different formats.

    Methods:
        - process_file: Process a file based on its extension
        - process_markdown: Extract text from Markdown files
        - process_python: Extract docstrings and comments from Python files
        - process_yaml_sigma: Parse YAML Sigma rule files
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Import PySigma for parsing YAML Sigma rules
        try:
            import sigma.collection  # noqa: F401

            self.PYSIGMA_AVAILABLE = True
        except ImportError as e:
            self.logger.warning(f"PySigma not available: {e}")
            self.PYSIGMA_AVAILABLE = False

    def process_file(self, file_path: str) -> Optional[str]:
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
        elif file_ext in [".yml", ".yaml"]:
            return self._process_yaml_sigma(file_path)
        else:
            # Fallback: read as plain text
            return self._read_plain_text(file_path)

    def _process_markdown(self, file_path: str) -> Optional[str]:
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

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Convert markdown to HTML and then extract text
            html_content = markdown.markdown(content)
            # Remove HTML tags for cleaner text
            text_content = re.sub(r"<[^>]+>", "", html_content)
            return text_content.strip()
        except Exception as e:
            self.logger.error(f"Error processing Markdown file {file_path}: {e}")
            return None

    def _process_python(self, file_path: str) -> Optional[str]:
        """
        Process Python files and extract docstrings and comments.

        Args:
            file_path (str): Path to the Python file

        Returns:
            Optional[str]: Extracted text content or None if processing fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
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

    def _process_yaml_sigma(self, file_path: str) -> Optional[str]:
        """
        Process YAML Sigma rule files and extract structured information.

        Args:
            file_path (str): Path to the YAML Sigma rule file

        Returns:
            Optional[str]: Extracted text content with metadata or None if processing fails
        """
        try:
            if not self.PYSIGMA_AVAILABLE:
                self.logger.warning(
                    "PySigma not available. Processing YAML as plain text."
                )
                # Fallback: read file as plain text
                return self._read_plain_text(file_path)

            from sigma.collection import SigmaCollection

            # Use PySigma to parse the rule
            with open(file_path, "r", encoding="utf-8") as f:
                yaml_content = f.read()

            parsed_collection = SigmaCollection.from_yaml(yaml_content)

            # Extract relevant information from the first rule in the collection
            extracted_info = []
            if len(parsed_collection.rules) > 0:
                rule = parsed_collection.rules[0]
                if hasattr(rule, "title") and rule.title:
                    extracted_info.append(f"Title: {rule.title}")
                if hasattr(rule, "description") and rule.description:
                    extracted_info.append(f"Description: {rule.description}")
                if hasattr(rule, "logsource") and rule.logsource:
                    extracted_info.append(f"Log Source: {rule.logsource}")
                if hasattr(rule, "detection"):
                    extracted_info.append(f"Detection: {str(rule.detection)[:200]}...")

            return "\n".join(extracted_info) if extracted_info else None
        except Exception as e:
            self.logger.error(f"Error processing YAML Sigma file {file_path}: {e}")
            return None

    def _read_plain_text(self, file_path: str) -> Optional[str]:
        """
        Read a file as plain text.

        Args:
            file_path (str): Path to the file

        Returns:
            Optional[str]: File content or None if reading fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
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
    ) -> Dict[str, Any]:
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
