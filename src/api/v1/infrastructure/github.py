"""GitHub Repository Management API v1."""

from pathlib import Path

from src.api.v1.base.repo_router import create_repo_router
from src.config.settings import get_config

router = create_repo_router(
    prefix="/api/v1/github",
    tags=["v1-github"],
    repos_dir_getter=lambda: Path(get_config().paths_github_dir),
    include_detail_endpoint=True,
    include_status_endpoint=True,
    include_outdated_check=True,
)
