"""
File Storage and Processing Directories Setup

This module provides utilities for setting up and managing file storage
directories for the SigmaHQ RAG application.
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileStorageSetup:
    """File storage and processing directories setup utilities."""

    def __init__(self, base_storage_path: str = "data/local"):
        """
        Initialize file storage setup.

        Args:
            base_storage_path: Base path for all storage directories
        """
        self.base_storage_path = Path(base_storage_path)
        self.logger = logging.getLogger(__name__)

        # Define directory structure
        self.directories = {
            "uploads": self.base_storage_path / "uploads",
            "processed": self.base_storage_path / "processed",
            "temp": self.base_storage_path / "temp",
            "logs": self.base_storage_path / "logs",
            "config": self.base_storage_path / "config",
            "cache": self.base_storage_path / "cache",
            "repositories": self.base_storage_path / "repositories",
            "embeddings": self.base_storage_path / "embeddings",
            "backups": self.base_storage_path / "backups",
            "exports": self.base_storage_path / "exports",
        }

    def create_directories(self) -> dict[str, bool]:
        """
        Create all required storage directories.

        Returns:
            Dictionary with creation status for each directory
        """
        results = {}

        self.logger.info("Creating file storage directories...")

        for dir_name, dir_path in self.directories.items():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)

                # Create .gitignore for each directory to prevent accidental commits
                gitignore_path = dir_path / ".gitignore"
                if not gitignore_path.exists():
                    with open(gitignore_path, "w") as f:
                        f.write("# Auto-generated .gitignore\n*")

                results[dir_name] = True
                self.logger.info(f"Created directory: {dir_path}")

            except Exception as e:
                results[dir_name] = False
                self.logger.error(f"Failed to create directory {dir_path}: {e}")

        return results

    def setup_directory_permissions(self) -> dict[str, bool]:
        """
        Set up appropriate permissions for storage directories.

        Returns:
            Dictionary with permission setup status for each directory
        """
        results = {}

        self.logger.info("Setting up directory permissions...")

        for dir_name, dir_path in self.directories.items():
            try:
                if dir_path.exists():
                    # On Windows, we can't set Unix-style permissions, but we can ensure the directory is writable
                    test_file = dir_path / ".permission_test"
                    test_file.touch()
                    test_file.unlink()
                    results[dir_name] = True
                    self.logger.debug(f"Permissions verified for: {dir_path}")
                else:
                    results[dir_name] = False
                    self.logger.warning(f"Directory does not exist: {dir_path}")

            except Exception as e:
                results[dir_name] = False
                self.logger.error(f"Failed to set permissions for {dir_path}: {e}")

        return results

    def create_directory_structure_info(self) -> dict[str, Any]:
        """
        Create information about the directory structure.

        Returns:
            Dictionary with directory structure information
        """
        info = {
            "base_storage_path": str(self.base_storage_path),
            "directories": {},
            "total_directories": len(self.directories),
            "created_directories": 0,
            "total_size": 0,
        }

        for dir_name, dir_path in self.directories.items():
            dir_info = {
                "path": str(dir_path),
                "exists": dir_path.exists(),
                "is_directory": dir_path.is_dir() if dir_path.exists() else False,
                "size": 0,
                "file_count": 0,
            }

            if dir_path.exists() and dir_path.is_dir():
                try:
                    # Calculate directory size
                    total_size = 0
                    file_count = 0

                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = Path(root) / file
                            try:
                                total_size += file_path.stat().st_size
                                file_count += 1
                            except OSError:
                                # Skip files that can't be accessed
                                pass

                    dir_info["size"] = total_size
                    dir_info["file_count"] = file_count
                    info["total_size"] += total_size
                    info["created_directories"] += 1

                except Exception as e:
                    self.logger.error(f"Error calculating size for {dir_path}: {e}")

            info["directories"][dir_name] = dir_info

        return info

    def create_sample_files(self) -> dict[str, bool]:
        """
        Create sample files in appropriate directories.

        Returns:
            Dictionary with sample file creation status
        """
        results = {}

        self.logger.info("Creating sample files...")

        # Create sample configuration files
        sample_configs = {
            "config": [
                ("app.json", '{"version": "1.0.0", "debug": false}'),
                (
                    "database.json",
                    '{"path": "data/local/sigmahq.db", "backup_enabled": true}',
                ),
                ("logging.json", '{"level": "INFO", "file": "logs/app.log"}'),
            ],
            "logs": [("readme.txt", "Application logs are stored in this directory.")],
            "cache": [
                ("readme.txt", "Temporary cache files are stored in this directory.")
            ],
            "backups": [
                (
                    "readme.txt",
                    "Database and configuration backups are stored in this directory.",
                )
            ],
        }

        for dir_name, files in sample_configs.items():
            if dir_name in self.directories:
                dir_path = self.directories[dir_name]
                for filename, content in files:
                    try:
                        file_path = dir_path / filename
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        results[f"{dir_name}/{filename}"] = True
                        self.logger.info(f"Created sample file: {file_path}")
                    except Exception as e:
                        results[f"{dir_name}/{filename}"] = False
                        self.logger.error(
                            f"Failed to create sample file {filename} in {dir_name}: {e}"
                        )

        return results

    def validate_storage_setup(self) -> dict[str, Any]:
        """
        Validate the complete storage setup.

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "directories_created": False,
            "permissions_set": False,
            "sample_files_created": False,
            "structure_info": {},
            "validation_passed": False,
        }

        self.logger.info("Validating storage setup...")

        # Step 1: Create directories
        dir_results = self.create_directories()
        validation_results["directories_created"] = all(dir_results.values())

        # Step 2: Set permissions
        if validation_results["directories_created"]:
            perm_results = self.setup_directory_permissions()
            validation_results["permissions_set"] = all(perm_results.values())

        # Step 3: Create sample files
        if validation_results["permissions_set"]:
            sample_results = self.create_sample_files()
            validation_results["sample_files_created"] = any(sample_results.values())

        # Get structure information
        validation_results["structure_info"] = self.create_directory_structure_info()

        # Overall validation
        validation_results["validation_passed"] = (
            validation_results["directories_created"]
            and validation_results["permissions_set"]
        )

        self.logger.info("Storage setup validation completed")
        return validation_results

    def cleanup_empty_directories(self) -> dict[str, bool]:
        """
        Clean up empty directories that shouldn't exist.

        Returns:
            Dictionary with cleanup status for each directory
        """
        results = {}

        self.logger.info("Cleaning up empty directories...")

        for dir_name, dir_path in self.directories.items():
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Check if directory is empty (ignoring .gitignore files)
                    files = [f for f in dir_path.iterdir() if f.name != ".gitignore"]
                    if not files:
                        # Directory is empty, remove it
                        dir_path.rmdir()
                        results[dir_name] = True
                        self.logger.info(f"Removed empty directory: {dir_path}")
                    else:
                        results[dir_name] = False
                        self.logger.debug(f"Directory not empty, keeping: {dir_path}")
                else:
                    results[dir_name] = True  # Already doesn't exist
                    self.logger.debug(f"Directory doesn't exist: {dir_path}")

            except Exception as e:
                results[dir_name] = False
                self.logger.error(f"Failed to clean up directory {dir_path}: {e}")

        return results


def setup_file_storage() -> dict[str, Any]:
    """
    Convenience function to set up file storage.

    Returns:
        Dictionary with setup results
    """
    storage_setup = FileStorageSetup()
    return storage_setup.validate_storage_setup()


if __name__ == "__main__":
    # Test file storage setup
    results = setup_file_storage()
    print("File Storage Setup Results:")
    for key, value in results.items():
        if key != "structure_info":
            print(f"  {key}: {value}")

    print("\nDirectory Structure Info:")
    structure_info = results["structure_info"]
    print(f"  Base Path: {structure_info['base_storage_path']}")
    print(f"  Total Directories: {structure_info['total_directories']}")
    print(f"  Created Directories: {structure_info['created_directories']}")
    print(f"  Total Size: {structure_info['total_size']} bytes")

    for dir_name, dir_info in structure_info["directories"].items():
        print(f"  {dir_name}:")
        print(f"    Path: {dir_info['path']}")
        print(f"    Exists: {dir_info['exists']}")
        print(f"    Size: {dir_info['size']} bytes")
        print(f"    Files: {dir_info['file_count']}")
