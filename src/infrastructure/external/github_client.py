"""
GitHub Client for SigmaHQ RAG application.

Provides GitHub API integration for repository management and file operations.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import requests

from ...shared import (
    DEFAULT_GITHUB_API_BASE_URL,
    SERVICE_GITHUB,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    BaseService,
    NetworkError,
    ServiceError,
)


@dataclass
class GitHubStats:
    """Statistics for GitHub client."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_api_calls: int = 0
    rate_limit_remaining: int = 0
    rate_limit_reset_time: float = 0.0
    memory_usage_mb: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class GitHubClient(BaseService):
    """
    GitHub API client for repository operations.
    
    Features:
    - Repository management
    - File operations
    - Rate limiting
    - Error handling
    - Authentication
    """

    def __init__(
        self,
        api_base_url: str = DEFAULT_GITHUB_API_BASE_URL,
        token: str | None = None,
        rate_limit_delay: float = 1.0,
    ):
        """
        Initialize the GitHub client.
        
        Args:
            api_base_url: GitHub API base URL
            token: GitHub API token
            rate_limit_delay: Delay between requests to avoid rate limiting
        """
        BaseService.__init__(self, f"{SERVICE_GITHUB}.github_client")
        
        # Configuration
        self.api_base_url = api_base_url
        self.token = token
        self.rate_limit_delay = rate_limit_delay
        
        # Statistics
        self.stats = GitHubStats()
        self._start_time = time.time()
        
        # Rate limiting
        self._last_request_time = 0

    def _get_headers(self) -> dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SigmaHQ-RAG",
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a request to the GitHub API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            
        Returns:
            Response data
        """
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request)
        
        self._last_request_time = time.time()
        
        try:
            url = f"{self.api_base_url}/{endpoint}"
            headers = self._get_headers()
            
            # Make request
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ServiceError(f"Unsupported HTTP method: {method}")
            
            # Update statistics
            self.stats.total_requests += 1
            self.stats.total_api_calls += 1
            
            # Check rate limiting
            if 'X-RateLimit-Remaining' in response.headers:
                self.stats.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            
            if 'X-RateLimit-Reset' in response.headers:
                self.stats.rate_limit_reset_time = float(response.headers['X-RateLimit-Reset'])
            
            # Handle response
            response.raise_for_status()
            self.stats.successful_requests += 1
            
            if response.content:
                return response.json()
            else:
                return {}
            
        except requests.exceptions.RequestException as e:
            self.stats.failed_requests += 1
            self.stats.last_error = str(e)
            self.logger.error(f"GitHub API request failed: {e}")
            raise NetworkError(f"GitHub API request failed: {str(e)}")
        except Exception as e:
            self.stats.failed_requests += 1
            self.stats.last_error = str(e)
            self.logger.error(f"GitHub API error: {e}")
            raise ServiceError(f"GitHub API error: {str(e)}")

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """
        Get repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository information
        """
        endpoint = f"repos/{owner}/{repo}"
        return await self._make_request("GET", endpoint)

    async def list_repository_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List files in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to list files from
            branch: Branch to list files from
            
        Returns:
            List of file information
        """
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        params = {}
        
        if branch:
            params["ref"] = branch
        
        response = await self._make_request("GET", endpoint, params=params)
        
        # Filter out directories and non-text files
        files = []
        for item in response:
            if item["type"] == "file" and self._is_text_file(item["name"]):
                files.append(item)
        
        return files

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str | None = None,
    ) -> str:
        """
        Get file content from a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            branch: Branch to get file from
            
        Returns:
            File content as string
        """
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        params = {}
        
        if branch:
            params["ref"] = branch
        
        response = await self._make_request("GET", endpoint, params=params)
        
        # Decode base64 content
        import base64
        content = base64.b64decode(response["content"]).decode("utf-8")
        
        return content

    async def search_files(
        self,
        query: str,
        owner: str | None = None,
        repo: str | None = None,
        file_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for files in repositories.
        
        Args:
            query: Search query
            owner: Repository owner (optional)
            repo: Repository name (optional)
            file_type: File type to search for (optional)
            
        Returns:
            List of search results
        """
        search_query = query
        
        if owner:
            search_query += f" user:{owner}"
        
        if repo:
            search_query += f" repo:{owner}/{repo}"
        
        if file_type:
            search_query += f" extension:{file_type}"
        
        endpoint = "search/code"
        params = {
            "q": search_query,
            "per_page": 100,
        }
        
        response = await self._make_request("GET", endpoint, params=params)
        
        return response.get("items", [])

    async def get_repository_commits(
        self,
        owner: str,
        repo: str,
        since: str | None = None,
        until: str | None = None,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get repository commits.
        
        Args:
            owner: Repository owner
            repo: Repository name
            since: Start date for commits
            until: End date for commits
            per_page: Number of commits per page
            
        Returns:
            List of commit information
        """
        endpoint = f"repos/{owner}/{repo}/commits"
        params = {
            "per_page": per_page,
        }
        
        if since:
            params["since"] = since
        
        if until:
            params["until"] = until
        
        response = await self._make_request("GET", endpoint, params=params)
        
        return response

    async def get_repository_branches(
        self,
        owner: str,
        repo: str,
    ) -> list[dict[str, Any]]:
        """
        Get repository branches.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of branch information
        """
        endpoint = f"repos/{owner}/{repo}/branches"
        response = await self._make_request("GET", endpoint)
        
        return response

    async def get_repository_tags(
        self,
        owner: str,
        repo: str,
    ) -> list[dict[str, Any]]:
        """
        Get repository tags.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of tag information
        """
        endpoint = f"repos/{owner}/{repo}/tags"
        response = await self._make_request("GET", endpoint)
        
        return response

    def _is_text_file(self, filename: str) -> bool:
        """
        Check if a file is likely to be a text file.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if file is likely text
        """
        text_extensions = [
            '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.yaml', '.yml', '.csv', '.log', '.rst', '.tex', '.sh', '.bat',
            '.ps1', '.ini', '.conf', '.config', '.env', '.sql', '.php',
            '.java', '.c', '.cpp', '.h', '.hpp', '.go', '.rust', '.rs',
            '.swift', '.kt', '.scala', '.r', '.matlab', '.m', '.vb',
        ]
        
        return any(filename.lower().endswith(ext) for ext in text_extensions)

    def get_rate_limit_status(self) -> dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Rate limit information
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/rate_limit",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error getting rate limit status: {e}")
            return {}

    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated.
        
        Returns:
            True if authenticated
        """
        if not self.token:
            return False
        
        try:
            response = requests.get(
                f"{self.api_base_url}/user",
                headers=self._get_headers()
            )
            return response.status_code == 200
            
        except Exception:
            return False

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []
        
        # Check authentication
        if not self.is_authenticated():
            status = STATUS_DEGRADED
            issues.append("Not authenticated")
        
        # Check error rate
        if self.stats.total_requests > 0:
            error_rate = self.stats.failed_requests / self.stats.total_requests
            if error_rate > 0.1:  # More than 10% error rate
                status = STATUS_DEGRADED
                issues.append(f"High error rate: {error_rate:.2%}")
        
        # Check rate limit
        rate_limit_status = self.get_rate_limit_status()
        if rate_limit_status:
            core_limit = rate_limit_status.get("resources", {}).get("core", {})
            remaining = core_limit.get("remaining", 0)
            if remaining < 100:  # Less than 100 requests remaining
                status = STATUS_DEGRADED
                issues.append(f"Low rate limit: {remaining} requests remaining")
        
        return {
            "service": SERVICE_GITHUB,
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "total_api_calls": self.stats.total_api_calls,
                "rate_limit_remaining": self.stats.rate_limit_remaining,
                "rate_limit_reset_time": self.stats.rate_limit_reset_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "rate_limit": rate_limit_status,
            "authenticated": self.is_authenticated(),
            "config": {
                "api_base_url": self.api_base_url,
                "rate_limit_delay": self.rate_limit_delay,
            },
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config": {
                "api_base_url": self.api_base_url,
                "rate_limit_delay": self.rate_limit_delay,
            },
            "stats": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "total_api_calls": self.stats.total_api_calls,
                "rate_limit_remaining": self.stats.rate_limit_remaining,
                "rate_limit_reset_time": self.stats.rate_limit_reset_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "last_error": self.stats.last_error,
                "uptime_seconds": time.time() - self._start_time,
            },
            "rate_limit": self.get_rate_limit_status(),
            "authenticated": self.is_authenticated(),
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("GitHub client cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during GitHub client cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory function
def create_github_client(
    api_base_url: str = DEFAULT_GITHUB_API_BASE_URL,
    token: str | None = None,
    rate_limit_delay: float = 1.0,
) -> GitHubClient:
    """Create a GitHub client with default configuration."""
    return GitHubClient(
        api_base_url=api_base_url,
        token=token,
        rate_limit_delay=rate_limit_delay,
    )