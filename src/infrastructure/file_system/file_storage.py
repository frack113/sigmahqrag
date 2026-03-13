"""
File Storage for SigmaHQ RAG application.

Provides secure file storage and management capabilities.
Handles file uploads, downloads, and metadata management.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from ...shared import (
    DEFAULT_ALLOWED_FILE_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE_MB,
    DEFAULT_UPLOAD_DIR,
    SERVICE_FILE_STORAGE,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    BaseService,
    FileError,
    FileMetadata,
    create_directory_if_not_exists,
    sanitize_filename,
    validate_file_upload,
)


@dataclass
class FileStorageStats:
    """Statistics for file storage."""
    total_files: int = 0
    total_size: int = 0
    uploads_today: int = 0
    downloads_today: int = 0
    failed_uploads: int = 0
    failed_downloads: int = 0
    memory_usage_mb: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class FileStorage(BaseService):
    """
    Secure file storage service for document management.
    
    Features:
    - File upload and download
    - Metadata management
    - File validation and security
    - Storage quota management
    - File organization by categories
    """

    def __init__(
        self,
        upload_dir: str = DEFAULT_UPLOAD_DIR,
        allowed_extensions: list[str] | None = None,
        max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
        max_storage_size_gb: int = 10,
    ):
        """
        Initialize the file storage service.
        
        Args:
            upload_dir: Directory for storing uploaded files
            allowed_extensions: List of allowed file extensions
            max_file_size_mb: Maximum file size in megabytes
            max_storage_size_gb: Maximum storage size in gigabytes
        """
        BaseService.__init__(self, f"{SERVICE_FILE_STORAGE}.file_storage")
        
        # Configuration
        self.upload_dir = upload_dir
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_FILE_EXTENSIONS
        self.max_file_size_mb = max_file_size_mb
        self.max_storage_size_gb = max_storage_size_gb
        
        # Statistics
        self.stats = FileStorageStats()
        self._start_time = time.time()
        
        # Initialize storage directory
        create_directory_if_not_exists(self.upload_dir)

    def get_file_path(self, file_id: str, category: str = "default") -> str:
        """
        Get the full path for a file.
        
        Args:
            file_id: Unique file identifier
            category: File category for organization
            
        Returns:
            Full file path
        """
        category_dir = os.path.join(self.upload_dir, category)
        create_directory_if_not_exists(category_dir)
        return os.path.join(category_dir, file_id)

    def generate_file_id(self, original_filename: str) -> str:
        """
        Generate a unique file ID based on the original filename.
        
        Args:
            original_filename: Original filename
            
        Returns:
            Unique file ID
        """
        # Create a hash of the filename for uniqueness
        file_hash = hashlib.md5(original_filename.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        safe_filename = sanitize_filename(original_filename)
        
        return f"{safe_filename}_{timestamp}_{file_hash}"

    def upload_file(
        self,
        file_path: str,
        original_filename: str,
        category: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> FileMetadata:
        """
        Upload a file to storage.
        
        Args:
            file_path: Path to the source file
            original_filename: Original filename
            category: File category
            metadata: Additional metadata
            
        Returns:
            File metadata
        """
        try:
            # Validate file
            if not validate_file_upload(
                file_path,
                allowed_extensions=self.allowed_extensions,
                max_size_mb=self.max_file_size_mb
            ):
                raise FileError("File validation failed")
            
            # Check storage quota
            if self.get_storage_usage() >= self.max_storage_size_gb * 1024 * 1024 * 1024:
                raise FileError("Storage quota exceeded")
            
            # Generate file ID and path
            file_id = self.generate_file_id(original_filename)
            destination_path = self.get_file_path(file_id, category)
            
            # Copy file to storage
            import shutil
            shutil.copy2(file_path, destination_path)
            
            # Create metadata
            file_info = self._get_file_info(destination_path)
            file_metadata = FileMetadata(
                file_id=file_id,
                original_filename=original_filename,
                file_path=destination_path,
                file_size=file_info["size"],
                file_type=file_info["type"],
                upload_time=time.time(),
                category=category,
                metadata=metadata or {},
                checksum=file_info["checksum"],
            )
            
            # Save metadata
            self._save_metadata(file_id, category, file_metadata)
            
            # Update statistics
            self.stats.total_files += 1
            self.stats.total_size += file_info["size"]
            self.stats.uploads_today += 1
            
            self.logger.info(f"File uploaded: {file_id} ({category})")
            return file_metadata
            
        except Exception as e:
            self.stats.failed_uploads += 1
            self.stats.last_error = str(e)
            self.logger.error(f"File upload failed: {e}")
            raise FileError(f"Upload failed: {str(e)}")

    def download_file(self, file_id: str, category: str = "default") -> str:
        """
        Get the path to download a file.
        
        Args:
            file_id: File identifier
            category: File category
            
        Returns:
            Path to the file
        """
        try:
            file_path = self.get_file_path(file_id, category)
            
            if not os.path.exists(file_path):
                raise FileError(f"File not found: {file_id}")
            
            self.stats.downloads_today += 1
            return file_path
            
        except Exception as e:
            self.stats.failed_downloads += 1
            self.stats.last_error = str(e)
            self.logger.error(f"File download failed: {e}")
            raise FileError(f"Download failed: {str(e)}")

    def delete_file(self, file_id: str, category: str = "default") -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_id: File identifier
            category: File category
            
        Returns:
            True if deletion successful
        """
        try:
            file_path = self.get_file_path(file_id, category)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Remove metadata
                metadata_path = self._get_metadata_path(file_id, category)
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
                
                # Update statistics
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                self.stats.total_files -= 1
                self.stats.total_size -= file_size
                
                self.logger.info(f"File deleted: {file_id} ({category})")
                return True
            else:
                self.logger.warning(f"File not found for deletion: {file_id}")
                return False
                
        except Exception as e:
            self.stats.last_error = str(e)
            self.logger.error(f"File deletion failed: {e}")
            return False

    def list_files(self, category: str | None = None) -> list[FileMetadata]:
        """
        List files in storage.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of file metadata
        """
        files = []
        
        search_dirs = [self.upload_dir]
        if category:
            search_dirs = [os.path.join(self.upload_dir, category)]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
                
            for root, dirs, filenames in os.walk(search_dir):
                for filename in filenames:
                    if filename.endswith('.metadata'):
                        continue
                    
                    # Get file metadata
                    file_id = filename
                    file_category = os.path.basename(root)
                    
                    try:
                        metadata = self.get_file_metadata(file_id, file_category)
                        if metadata:
                            files.append(metadata)
                    except Exception as e:
                        self.logger.warning(f"Could not load metadata for {file_id}: {e}")
        
        return files

    def get_file_metadata(self, file_id: str, category: str = "default") -> FileMetadata | None:
        """
        Get metadata for a file.
        
        Args:
            file_id: File identifier
            category: File category
            
        Returns:
            File metadata or None if not found
        """
        metadata_path = self._get_metadata_path(file_id, category)
        
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path) as f:
                data = json.load(f)
                return FileMetadata(**data)
        except Exception as e:
            self.logger.error(f"Error loading metadata for {file_id}: {e}")
            return None

    def update_file_metadata(
        self,
        file_id: str,
        category: str,
        metadata: dict[str, Any],
    ) -> bool:
        """
        Update file metadata.
        
        Args:
            file_id: File identifier
            category: File category
            metadata: Updated metadata
            
        Returns:
            True if update successful
        """
        try:
            file_metadata = self.get_file_metadata(file_id, category)
            if not file_metadata:
                return False
            
            # Update metadata
            file_metadata.metadata.update(metadata)
            file_metadata.last_modified = time.time()
            
            # Save updated metadata
            self._save_metadata(file_id, category, file_metadata)
            
            self.logger.info(f"Metadata updated for {file_id}")
            return True
            
        except Exception as e:
            self.stats.last_error = str(e)
            self.logger.error(f"Metadata update failed for {file_id}: {e}")
            return False

    def get_storage_usage(self) -> int:
        """
        Get current storage usage in bytes.
        
        Returns:
            Storage usage in bytes
        """
        total_size = 0
        
        for root, dirs, files in os.walk(self.upload_dir):
            for file in files:
                if not file.endswith('.metadata'):
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
        
        return total_size

    def get_storage_quota_info(self) -> dict[str, Any]:
        """
        Get storage quota information.
        
        Returns:
            Storage quota information
        """
        current_usage = self.get_storage_usage()
        max_storage_bytes = self.max_storage_size_gb * 1024 * 1024 * 1024
        
        return {
            "current_usage_bytes": current_usage,
            "current_usage_gb": current_usage / (1024 * 1024 * 1024),
            "max_storage_gb": self.max_storage_size_gb,
            "max_storage_bytes": max_storage_bytes,
            "usage_percentage": (current_usage / max_storage_bytes) * 100,
            "remaining_bytes": max_storage_bytes - current_usage,
            "remaining_gb": (max_storage_bytes - current_usage) / (1024 * 1024 * 1024),
        }

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """
        Clean up files older than specified age.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        for root, dirs, files in os.walk(self.upload_dir):
            for file in files:
                if file.endswith('.metadata'):
                    continue
                
                file_path = os.path.join(root, file)
                metadata_path = self._get_metadata_path(file, os.path.basename(root))
                
                try:
                    # Check file modification time
                    if os.path.getmtime(file_path) < cutoff_time:
                        # Delete file and metadata
                        os.remove(file_path)
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                        
                        deleted_count += 1
                        
                        # Update statistics
                        file_size = os.path.getsize(file_path)
                        self.stats.total_files -= 1
                        self.stats.total_size -= file_size
                        
                except Exception as e:
                    self.logger.error(f"Error deleting old file {file_path}: {e}")
        
        self.logger.info(f"Cleaned up {deleted_count} old files")
        return deleted_count

    def _get_file_info(self, file_path: str) -> dict[str, Any]:
        """Get file information."""
        file_size = os.path.getsize(file_path)
        file_type = self._get_file_type(file_path)
        checksum = self._calculate_checksum(file_path)
        
        return {
            "size": file_size,
            "type": file_type,
            "checksum": checksum,
        }

    def _get_file_type(self, file_path: str) -> str:
        """Get file type based on extension."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        text_types = ['.txt', '.md']
        document_types = ['.pdf', '.docx', '.doc']
        data_types = ['.csv', '.json', '.xml']
        
        if file_ext in text_types:
            return "text"
        elif file_ext in document_types:
            return "document"
        elif file_ext in data_types:
            return "data"
        else:
            return "unknown"

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _save_metadata(self, file_id: str, category: str, metadata: FileMetadata) -> None:
        """Save file metadata to disk."""
        metadata_path = self._get_metadata_path(file_id, category)
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata.__dict__, f, indent=2)

    def _get_metadata_path(self, file_id: str, category: str) -> str:
        """Get the path for file metadata."""
        return os.path.join(self.upload_dir, category, f"{file_id}.metadata")

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []
        
        # Check storage usage
        quota_info = self.get_storage_quota_info()
        if quota_info["usage_percentage"] > 90:  # More than 90% usage
            status = STATUS_DEGRADED
            issues.append(f"High storage usage: {quota_info['usage_percentage']:.1f}%")
        
        # Check error rate
        total_operations = self.stats.uploads_today + self.stats.downloads_today
        if total_operations > 0:
            error_rate = (self.stats.failed_uploads + self.stats.failed_downloads) / total_operations
            if error_rate > 0.1:  # More than 10% error rate
                status = STATUS_DEGRADED
                issues.append(f"High error rate: {error_rate:.2%}")
        
        return {
            "service": SERVICE_FILE_STORAGE,
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": {
                "total_files": self.stats.total_files,
                "total_size": self.stats.total_size,
                "uploads_today": self.stats.uploads_today,
                "downloads_today": self.stats.downloads_today,
                "failed_uploads": self.stats.failed_uploads,
                "failed_downloads": self.stats.failed_downloads,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "storage_quota": quota_info,
            "config": {
                "upload_dir": self.upload_dir,
                "allowed_extensions": self.allowed_extensions,
                "max_file_size_mb": self.max_file_size_mb,
                "max_storage_size_gb": self.max_storage_size_gb,
            },
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config": {
                "upload_dir": self.upload_dir,
                "allowed_extensions": self.allowed_extensions,
                "max_file_size_mb": self.max_file_size_mb,
                "max_storage_size_gb": self.max_storage_size_gb,
            },
            "stats": {
                "total_files": self.stats.total_files,
                "total_size": self.stats.total_size,
                "uploads_today": self.stats.uploads_today,
                "downloads_today": self.stats.downloads_today,
                "failed_uploads": self.stats.failed_uploads,
                "failed_downloads": self.stats.failed_downloads,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "storage_quota": self.get_storage_quota_info(),
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up old files
            self.cleanup_old_files(max_age_days=7)  # Clean up files older than 7 days
            self.logger.info("File storage cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during file storage cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory function
def create_file_storage(
    upload_dir: str = DEFAULT_UPLOAD_DIR,
    allowed_extensions: list[str] | None = None,
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    max_storage_size_gb: int = 10,
) -> FileStorage:
    """Create a file storage service with default configuration."""
    return FileStorage(
        upload_dir=upload_dir,
        allowed_extensions=allowed_extensions,
        max_file_size_mb=max_file_size_mb,
        max_storage_size_gb=max_storage_size_gb,
    )