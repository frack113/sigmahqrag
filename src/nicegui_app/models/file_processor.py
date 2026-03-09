"""
File Processor for NiceGUI - Handles processing of different file formats for RAG indexing

This module provides functionality to process various file formats commonly found in
code repositories and documentation, extracting text content for RAG indexing.
"""

import os
import logging
import json
import re
from typing import Optional, Dict, Any, List
from datetime import datetime


class FileProcessor:
    """
    A service to process different file formats and extract text content for RAG indexing.

    Supported file formats:
    - Text files (.txt, .md, .rst, .org)
    - Code files (.py, .js, .java, .cpp, .c, .h, .hpp, .cs, .php, .rb, .go, .rs, .swift, .kt)
    - Documentation files (.json, .yaml, .yml, .xml, .html, .htm)
    - Configuration files (.ini, .cfg, .conf, .properties, .toml)
    - Data files (.csv, .tsv, .sql)
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Supported file extensions and their processing methods
        self.supported_extensions = {
            # Text and documentation
            '.txt': self._process_text_file,
            '.md': self._process_markdown_file,
            '.rst': self._process_text_file,
            '.org': self._process_text_file,
            
            # Code files
            '.py': self._process_code_file,
            '.js': self._process_code_file,
            '.java': self._process_code_file,
            '.cpp': self._process_code_file,
            '.c': self._process_code_file,
            '.h': self._process_code_file,
            '.hpp': self._process_code_file,
            '.cs': self._process_code_file,
            '.php': self._process_code_file,
            '.rb': self._process_code_file,
            '.go': self._process_code_file,
            '.rs': self._process_code_file,
            '.swift': self._process_code_file,
            '.kt': self._process_code_file,
            
            # Documentation and data
            '.json': self._process_json_file,
            '.yaml': self._process_yaml_file,
            '.yml': self._process_yaml_file,
            '.xml': self._process_xml_file,
            '.html': self._process_html_file,
            '.htm': self._process_html_file,
            
            # Configuration
            '.ini': self._process_text_file,
            '.cfg': self._process_text_file,
            '.conf': self._process_text_file,
            '.properties': self._process_text_file,
            '.toml': self._process_toml_file,
            
            # Data files
            '.csv': self._process_csv_file,
            '.tsv': self._process_tsv_file,
            '.sql': self._process_sql_file,
        }

    def process_file(self, file_path: str) -> Optional[str]:
        """
        Process a file and extract its text content.

        Args:
            file_path (str): Path to the file to process

        Returns:
            Optional[str]: Extracted text content or None if processing failed
        """
        try:
            if not os.path.exists(file_path):
                self.logger.warning(f"File not found: {file_path}")
                return None

            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext not in self.supported_extensions:
                self.logger.debug(f"Unsupported file format: {file_ext} for {file_path}")
                return None

            # Get the appropriate processing method
            process_method = self.supported_extensions[file_ext]
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f"Could not read file {file_path}: {e}")
                return None

            # Process the content
            processed_content = process_method(content, file_path)
            
            if processed_content:
                self.logger.info(f"Successfully processed: {file_path}")
                return processed_content
            else:
                self.logger.warning(f"No content extracted from: {file_path}")
                return None

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return None

    def _process_text_file(self, content: str, file_path: str) -> Optional[str]:
        """Process plain text files."""
        if not content or not content.strip():
            return None
        
        # Clean up excessive whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', content)
        return cleaned.strip()

    def _process_markdown_file(self, content: str, file_path: str) -> Optional[str]:
        """Process Markdown files, preserving structure but removing formatting."""
        if not content:
            return None

        # Remove markdown formatting but preserve structure
        # Remove headers but keep the text
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Remove bold and italic formatting
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        content = re.sub(r'__(.*?)__', r'\1', content)
        content = re.sub(r'_(.*?)_', r'\1', content)
        
        # Remove links but keep text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # Remove code blocks and inline code
        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # Remove images
        content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
        
        # Remove horizontal rules
        content = re.sub(r'^[-*_]{3,}', '', content, flags=re.MULTILINE)
        
        # Clean up excessive whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', content)
        return cleaned.strip()

    def _process_code_file(self, content: str, file_path: str) -> Optional[str]:
        """Process code files, extracting meaningful content."""
        if not content:
            return None

        # Remove comments based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.py']:
            # Python comments
            content = re.sub(r'#.*', '', content)
        elif file_ext in ['.js', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.go', '.rs', '.swift', '.kt']:
            # C-style comments
            content = re.sub(r'//.*', '', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Extract function/method definitions, class definitions, and meaningful comments
        meaningful_content = []
        
        # Add file path context
        meaningful_content.append(f"File: {os.path.basename(file_path)}")
        meaningful_content.append(f"Path: {file_path}")
        
        # Extract class definitions
        class_pattern = r'(?:class|interface|struct)\s+(\w+)'
        classes = re.findall(class_pattern, content, re.IGNORECASE)
        if classes:
            meaningful_content.append(f"Classes/Structs: {', '.join(classes)}")
        
        # Extract function/method definitions
        func_pattern = r'(?:def|function|func|method)\s+(\w+)'
        functions = re.findall(func_pattern, content, re.IGNORECASE)
        if functions:
            meaningful_content.append(f"Functions/Methods: {', '.join(functions)}")
        
        # Add the cleaned content
        meaningful_content.append("Content:")
        meaningful_content.append(content)
        
        result = '\n'.join(meaningful_content)
        return result if result.strip() else None

    def _process_json_file(self, content: str, file_path: str) -> Optional[str]:
        """Process JSON files."""
        if not content:
            return None

        try:
            # Parse JSON to extract meaningful structure
            data = json.loads(content)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            # If not valid JSON, treat as text
            return self._process_text_file(content, file_path)

    def _process_yaml_file(self, content: str, file_path: str) -> Optional[str]:
        """Process YAML files."""
        if not content:
            return None

        # For YAML, we'll extract key information
        lines = content.split('\n')
        meaningful_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):  # Skip comments and empty lines
                meaningful_lines.append(line)
        
        return '\n'.join(meaningful_lines) if meaningful_lines else None

    def _process_xml_file(self, content: str, file_path: str) -> Optional[str]:
        """Process XML files."""
        if not content:
            return None

        # Extract text content from XML tags
        # Remove tags but keep content
        text_content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', text_content)
        return cleaned.strip()

    def _process_html_file(self, content: str, file_path: str) -> Optional[str]:
        """Process HTML files."""
        if not content:
            return None

        # Remove HTML tags
        text_content = re.sub(r'<[^>]+>', '', content)
        
        # Remove script and style blocks
        text_content = re.sub(r'<script[^>]*>.*?</script>', '', text_content, flags=re.DOTALL)
        text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL)
        
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', text_content)
        return cleaned.strip()

    def _process_toml_file(self, content: str, file_path: str) -> Optional[str]:
        """Process TOML files."""
        if not content:
            return None

        # Extract key-value pairs
        lines = content.split('\n')
        meaningful_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                meaningful_lines.append(line)
        
        return '\n'.join(meaningful_lines) if meaningful_lines else None

    def _process_csv_file(self, content: str, file_path: str) -> Optional[str]:
        """Process CSV files."""
        if not content:
            return None

        # Extract first few lines to understand structure
        lines = content.split('\n')[:10]  # Limit to first 10 lines
        return '\n'.join(lines).strip()

    def _process_tsv_file(self, content: str, file_path: str) -> Optional[str]:
        """Process TSV files."""
        if not content:
            return None

        # Similar to CSV but with tabs
        lines = content.split('\n')[:10]  # Limit to first 10 lines
        return '\n'.join(lines).strip()

    def _process_sql_file(self, content: str, file_path: str) -> Optional[str]:
        """Process SQL files."""
        if not content:
            return None

        # Extract SQL statements and structure
        meaningful_content = []
        
        # Add file context
        meaningful_content.append(f"SQL File: {os.path.basename(file_path)}")
        
        # Extract CREATE statements
        create_statements = re.findall(r'CREATE\s+(TABLE|VIEW|INDEX|PROCEDURE)\s+[^;]+', content, re.IGNORECASE)
        if create_statements:
            meaningful_content.append(f"SQL Objects: {', '.join(create_statements)}")
        
        # Extract table names from CREATE TABLE statements
        table_names = re.findall(r'CREATE\s+TABLE\s+[^(\s]+', content, re.IGNORECASE)
        if table_names:
            meaningful_content.append(f"Tables: {', '.join(table_names)}")
        
        # Add the SQL content
        meaningful_content.append("SQL Content:")
        meaningful_content.append(content)
        
        result = '\n'.join(meaningful_content)
        return result if result.strip() else None

    def create_document_id(self, file_path: str) -> str:
        """
        Create a unique document ID for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            str: Unique document ID
        """
        # Use a hash of the file path to create a unique ID
        import hashlib
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        return f"file_{file_hash}"

    def create_metadata(self, file_path: str, repo_name: str, branch: str, repo_dir: str) -> Dict[str, Any]:
        """
        Create metadata for a processed file.

        Args:
            file_path (str): Path to the file
            repo_name (str): Name of the repository
            branch (str): Branch name
            repo_dir (str): Repository directory

        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        relative_path = os.path.relpath(file_path, repo_dir)
        
        # Get file stats
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except:
            file_size = 0
            modified_time = datetime.now().isoformat()

        metadata = {
            "file_name": file_name,
            "file_path": file_path,
            "relative_path": relative_path,
            "file_extension": file_ext,
            "file_size": file_size,
            "repository": repo_name,
            "branch": branch,
            "processed_at": datetime.now().isoformat(),
            "modified_time": modified_time,
            "file_type": self._get_file_type(file_ext)
        }
        
        return metadata

    def _get_file_type(self, file_extension: str) -> str:
        """Get a human-readable file type from extension."""
        file_type_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C Header',
            '.hpp': 'C++ Header',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.xml': 'XML',
            '.html': 'HTML',
            '.htm': 'HTML',
            '.csv': 'CSV',
            '.sql': 'SQL',
        }
        
        return file_type_map.get(file_extension, 'Unknown')

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(self.supported_extensions.keys())

    def is_supported_file(self, file_path: str) -> bool:
        """Check if a file has a supported extension."""
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in self.supported_extensions