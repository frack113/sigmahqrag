"""Sigma Specification Repository Management API v1."""

import logging
from pathlib import Path

from src.api.v1.base.repo_router import create_repo_router
from src.config.settings import get_config
from src.infrastructure.database import DatabaseService

logger = logging.getLogger(__name__)


def _spec_repos_dir() -> Path:
    return Path(get_config().paths_spec_repos_dir).resolve()


def _cleanup_sigma_spec(org: str, name: str) -> None:
    db = DatabaseService.get_instance()
    db.delete_sigma_spec_by_org_repo(org, name)
    logger.info("Cleaned up sigma_spec entries for %s/%s", org, name)


router = create_repo_router(
    prefix="/api/v1/spec",
    tags=["v1-spec"],
    repos_dir_getter=_spec_repos_dir,
    include_selected_dirs_endpoint=True,
    include_outdated_check=False,
    on_delete_cleanup=_cleanup_sigma_spec,
    use_get_for_sync=True,
)
