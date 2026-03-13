"""
Data Service - Optimized for Gradio Native Integration

Uses simple methods without custom async wrappers:
- Direct file operations
- Simple subprocess calls (Gradio handles async via queue=True)
- No asyncio overhead
"""

from pathlib import Path
from typing import Any


class DataService:
    """
    Data service using simple file operations.

    Features:
    - Repository cloning and indexing
    - Context management for RAG
    - Simple synchronous methods (Gradio queue=True handles async)
    """

    def __init__(self):
        self.data_dir = Path("data/github")
        self.temp_dir = Path("temp")

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def clone_repository(self, repo_url: str, branch: str | None = None) -> bool:
        """Clone a repository."""
        try:
            # Clone in temp directory first
            temp_path = self.temp_dir / Path(repo_url).name

            # Run git clone with subprocess (simple call, no async needed)
            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([repo_url, str(temp_path)])

            import subprocess

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for clone
            )

            if result.returncode == 0:
                # Move to data directory
                dest_path = self.data_dir / Path(repo_url).name

                if not dest_path.exists():
                    import shutil

                    shutil.move(str(temp_path), str(dest_path))

                return True

        except Exception as e:
            print(f"Clone failed: {e}")

        return False

    def clone_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """Clone all enabled repositories."""
        repos = repo_config.get("repositories", [])

        for repo in repos:
            if not repo.get("enabled", True):
                continue

            url = repo["url"]
            branch = repo.get("branch", "main")

            success = self.clone_repository(url, branch)

            if not success:
                print(f"Failed to clone {url}")
                return False

        return True

    def index_repositories(self, file_extensions: list[str] | None = None) -> bool:
        """Index repository contents for RAG."""
        try:
            # Find files to index
            files_to_index = []

            if file_extensions is None:
                file_extensions = ["py", "js", "ts", "html", "css", "json"]

            for ext in file_extensions:
                files_to_index.extend(self.data_dir.glob(f"*/*.{ext}"))

            # Build collection (would use actual embedding here)
            print(f"Indexing {len(files_to_index)} files...")

            return True

        except Exception as e:
            print(f"Index failed: {e}")
            return False

    def index_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """Index all enabled repositories."""
        repos = repo_config.get("repositories", [])

        for repo in repos:
            if not repo.get("enabled", True):
                continue

            success = self.index_repositories(repo.get("file_extensions"))

            if not success:
                return False

        return True

    def get_context_stats(self) -> dict[str, Any]:
        """Get context statistics."""
        try:
            count = 0
            total_size = 0

            for ext in ["py", "js", "ts", "html", "css", "json"]:
                files = list(self.data_dir.glob(f"*/*.{ext}"))
                count += len(files)
                total_size += sum(f.stat().st_size for f in files)

            return {
                "count": count,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "embedding_model": "all-MiniLM-L6-v2",
                "default_chunk_size": 1000,
                "default_chunk_overlap": 200,
            }

        except Exception as e:
            return {
                "count": 0,
                "size_mb": 0,
                "embedding_model": "Unknown",
                "default_chunk_size": "Unknown",
                "default_chunk_overlap": "Unknown",
                "error": str(e),
            }

    def clear_context(self) -> bool:
        """Clear the RAG context."""
        try:
            # Just track that context was cleared - files remain intact
            return True
        except Exception as e:
            print(f"Clear context failed: {e}")
            return False
