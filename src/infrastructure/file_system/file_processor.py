"""
File Processor for SigmaHQ RAG application.

Handles document processing and text extraction from various file formats.
Provides a clean interface for processing uploaded files.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from src.shared import (
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_TEMP_DIR,
    SERVICE_FILE_PROCESSOR,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    BaseService,
    FileError,
    chunk_text,
    create_directory_if_not_exists,
    get_file_info,
    validate_file_upload,
)

# Default allowed file extensions
DEFAULT_ALLOWED_FILE_EXTENSIONS = [
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".doc",
    ".csv",
    ".json",
    ".xml",
]


@dataclass
class FileProcessorStats:
    """Statistics for file processor."""

    total_files_processed: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_size_processed: int = 0
    average_processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class FileProcessor(BaseService):
    """
    File processor for document processing and text extraction.

    Supports multiple file formats:
    - Text files (.txt, .md)
    - PDF files (.pdf)
    - Word documents (.docx, .doc)
    - CSV files (.csv)
    - JSON files (.json)
    - XML files (.xml)

    Features:
    - File validation and security checks
    - Text extraction from various formats
    - Chunking for RAG processing
    - Metadata extraction
    - Performance monitoring
    """

    def __init__(
        self,
        allowed_extensions: list[str] | None = None,
        max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
        temp_dir: str = DEFAULT_TEMP_DIR,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize the file processor.

        Args:
            allowed_extensions: List of allowed file extensions
            max_file_size_mb: Maximum file size in megabytes
            temp_dir: Temporary directory for processing
            chunk_size: Default chunk size for text processing
            chunk_overlap: Default chunk overlap for text processing
        """
        BaseService.__init__(self, f"{SERVICE_FILE_PROCESSOR}.file_processor")

        # Configuration
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_FILE_EXTENSIONS
        self.max_file_size_mb = max_file_size_mb
        self.temp_dir = temp_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Statistics
        self.stats = FileProcessorStats()
        self._start_time = time.time()

        # Initialize temp directory
        create_directory_if_not_exists(self.temp_dir)

    def get_file_type(self, file_path: str) -> str:
        """
        Determine the file type based on extension.

        Args:
            file_path: Path to the file

        Returns:
            File type string
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        text_types = [".txt", ".md"]
        document_types = [".pdf", ".docx", ".doc"]
        data_types = [".csv", ".json", ".xml"]

        if file_ext in text_types:
            return "text"
        elif file_ext in document_types:
            return "document"
        elif file_ext in data_types:
            return "data"
        else:
            return "unknown"

    async def extract_text(self, file_path: str) -> tuple[str, dict[str, Any]]:
        """
        Extract text from a file based on its type.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (extracted_text, metadata)
        """
        start_time = time.time()

        try:
            file_type = self.get_file_type(file_path)
            metadata = get_file_info(file_path)

            if file_type == "text":
                text = await self._extract_text_from_text_file(file_path)
            elif file_type == "document":
                text = await self._extract_text_from_document(file_path)
            elif file_type == "data":
                text = await self._extract_text_from_data_file(file_path)
            else:
                raise FileError(f"Unsupported file type: {file_type}")

            # Update statistics
            self.stats.total_files_processed += 1
            self.stats.successful_files += 1
            self.stats.total_size_processed += metadata.get("file_size", 0)

            processing_time = time.time() - start_time

            # Update average processing time (moving average)
            if self.stats.successful_files > 1:
                self.stats.average_processing_time = (
                    (
                        self.stats.average_processing_time
                        * (self.stats.successful_files - 1)
                    )
                    + processing_time
                ) / self.stats.successful_files
            else:
                self.stats.average_processing_time = processing_time

            # Add processing metadata
            metadata.update(
                {
                    "file_type": file_type,
                    "processing_time": processing_time,
                    "text_length": len(text),
                    "chunk_count": len(
                        chunk_text(text, self.chunk_size, self.chunk_overlap)
                    ),
                }
            )

            self.logger.info(f"Successfully processed file: {file_path} ({file_type})")
            return text, metadata

        except Exception as e:
            self.stats.failed_files += 1
            self.stats.last_error = str(e)
            self.logger.error(f"Error processing file {file_path}: {e}")
            raise FileError(f"Failed to process file: {str(e)}")

    async def _extract_text_from_text_file(self, file_path: str) -> str:
        """Extract text from plain text or markdown files."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as file:
                return file.read()
        except Exception as e:
            raise FileError(f"Error reading text file: {str(e)}")

    async def _extract_text_from_document(self, file_path: str) -> str:
        """Extract text from PDF or Word documents."""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".pdf":
            return await self._extract_text_from_pdf(file_path)
        elif file_ext in [".docx", ".doc"]:
            return await self._extract_text_from_docx(file_path)
        else:
            raise FileError(f"Unsupported document type: {file_ext}")

    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2

            text = ""
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"

            return text
        except ImportError:
            raise FileError("PyPDF2 not available for PDF processing")
        except Exception as e:
            raise FileError(f"Error extracting text from PDF: {str(e)}")

    async def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document

            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            return text
        except ImportError:
            raise FileError("python-docx not available for DOCX processing")
        except Exception as e:
            raise FileError(f"Error extracting text from DOCX: {str(e)}")

    async def _extract_text_from_data_file(self, file_path: str) -> str:
        """Extract text from CSV, JSON, or XML files."""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".csv":
            return await self._extract_text_from_csv(file_path)
        elif file_ext == ".json":
            return await self._extract_text_from_json(file_path)
        elif file_ext == ".xml":
            return await self._extract_text_from_xml(file_path)
        else:
            raise FileError(f"Unsupported data file type: {file_ext}")

    async def _extract_text_from_csv(self, file_path: str) -> str:
        """Extract text from CSV file."""
        try:
            import csv

            text = ""
            with open(file_path, encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    text += " | ".join(row) + "\n"

            return text
        except Exception as e:
            raise FileError(f"Error extracting text from CSV: {str(e)}")

    async def _extract_text_from_json(self, file_path: str) -> str:
        """Extract text from JSON file."""
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
                return json.dumps(data, indent=2)
        except Exception as e:
            raise FileError(f"Error extracting text from JSON: {str(e)}")

    async def _extract_text_from_xml(self, file_path: str) -> str:
        """Extract text from XML file."""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(file_path)
            root = tree.getroot()

            def extract_text_recursive(element):
                text = element.text or ""
                for child in element:
                    text += extract_text_recursive(child)
                return text

            return extract_text_recursive(root)
        except Exception as e:
            raise FileError(f"Error extracting text from XML: {str(e)}")

    async def process_file(
        self,
        file_path: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        """
        Process a file and return chunks with metadata.

        Args:
            file_path: Path to the file
            chunk_size: Size of each chunk (uses default if None)
            chunk_overlap: Overlap between chunks (uses default if None)

        Returns:
            Tuple of (text_chunks, metadata)
        """
        # Validate file
        if not validate_file_upload(
            file_path,
            allowed_extensions=self.allowed_extensions,
            max_size_mb=self.max_file_size_mb,
        ):
            raise FileError("File validation failed")

        # Extract text
        text, metadata = await self.extract_text(file_path)

        # Chunk text
        actual_chunk_size = chunk_size or self.chunk_size
        actual_chunk_overlap = chunk_overlap or self.chunk_overlap

        chunks = chunk_text(text, actual_chunk_size, actual_chunk_overlap)

        # Add chunking metadata
        metadata.update(
            {
                "chunk_size": actual_chunk_size,
                "chunk_overlap": actual_chunk_overlap,
                "chunk_count": len(chunks),
                "total_chunks": len(chunks),
            }
        )

        return chunks, metadata

    async def process_multiple_files(
        self,
        file_paths: list[str],
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[tuple[list[str], dict[str, Any]]]:
        """
        Process multiple files efficiently.

        Args:
            file_paths: List of file paths
            chunk_size: Size of each chunk (uses default if None)
            chunk_overlap: Overlap between chunks (uses default if None)

        Returns:
            List of (text_chunks, metadata) tuples
        """
        results = []

        for file_path in file_paths:
            try:
                chunks, metadata = await self.process_file(
                    file_path, chunk_size, chunk_overlap
                )
                results.append((chunks, metadata))
            except Exception as e:
                self.logger.error(f"Failed to process file {file_path}: {e}")
                results.append(([], {"error": str(e), "file_path": file_path}))

        return results

    def validate_file(self, file_path: str) -> bool:
        """
        Validate a file for processing.

        Args:
            file_path: Path to the file

        Returns:
            True if file is valid for processing
        """
        try:
            return validate_file_upload(
                file_path,
                allowed_extensions=self.allowed_extensions,
                max_size_mb=self.max_file_size_mb,
            )
        except Exception as e:
            self.logger.error(f"File validation error: {e}")
            return False

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as hexadecimal string
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating file hash: {e}")
            return ""

    def cleanup_temp_files(self, age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.

        Args:
            age_hours: Age threshold in hours

        Returns:
            Number of files deleted
        """
        from src.shared.utils import cleanup_temp_files

        return cleanup_temp_files(self.temp_dir, age_hours)

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []

        # Check error rate
        if self.stats.total_files_processed > 0:
            error_rate = self.stats.failed_files / self.stats.total_files_processed
            if error_rate > 0.1:  # More than 10% error rate
                status = STATUS_DEGRADED
                issues.append(f"High error rate: {error_rate:.2%}")

        # Check processing time
        if self.stats.average_processing_time > 60.0:  # More than 60 seconds average
            status = STATUS_DEGRADED
            issues.append(
                f"High processing time: {self.stats.average_processing_time:.2f}s"
            )

        # Check memory usage
        if self.stats.memory_usage_mb > 512.0:  # More than 512MB
            status = STATUS_DEGRADED
            issues.append(f"High memory usage: {self.stats.memory_usage_mb:.2f}MB")

        return {
            "service": SERVICE_FILE_PROCESSOR,
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": {
                "total_files_processed": self.stats.total_files_processed,
                "successful_files": self.stats.successful_files,
                "failed_files": self.stats.failed_files,
                "total_size_processed": self.stats.total_size_processed,
                "average_processing_time": self.stats.average_processing_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "config": {
                "allowed_extensions": self.allowed_extensions,
                "max_file_size_mb": self.max_file_size_mb,
                "temp_dir": self.temp_dir,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
            },
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config": {
                "allowed_extensions": self.allowed_extensions,
                "max_file_size_mb": self.max_file_size_mb,
                "temp_dir": self.temp_dir,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
            },
            "stats": {
                "total_files_processed": self.stats.total_files_processed,
                "successful_files": self.stats.successful_files,
                "failed_files": self.stats.failed_files,
                "total_size_processed": self.stats.total_size_processed,
                "average_processing_time": self.stats.average_processing_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up temp files
            self.cleanup_temp_files(age_hours=1)  # Clean up files older than 1 hour
            self.logger.info("File processor cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during file processor cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory function
def create_file_processor(
    allowed_extensions: list[str] | None = None,
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    temp_dir: str = DEFAULT_TEMP_DIR,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> FileProcessor:
    """Create a file processor with default configuration."""
    return FileProcessor(
        allowed_extensions=allowed_extensions,
        max_file_size_mb=max_file_size_mb,
        temp_dir=temp_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
