import logging

from src.worker.base import BaseWorker
from src.worker.enums import WorkerName, WorkerStatus
from src.back.github.git import list_repos, get_metadata, save_metadata

logger = logging.getLogger(__name__)


class LocalRepoSyncWorker(BaseWorker):
    """Syncs filesystem git repositories into git_metadata table."""

    def process(self, task: dict) -> None:
        self.dispatcher.update_worker_state(
            worker_type=WorkerName.LOCAL_REPO_SYNC,
            status=WorkerStatus.RUNNING,
            current_task_id=task.get("task_id", ""),
        )

        logger.info("[LocalRepoSyncWorker] Starting repo sync...")

        synced = 0
        skipped = 0

        for repo in list_repos():
            repo_key = f"{repo['org']}/{repo['name']}"
            if get_metadata(repo["org"], repo["name"]) is None:
                save_metadata(
                    repo["org"],
                    repo["name"],
                    {
                        "org": repo["org"],
                        "name": repo["name"],
                        "url": repo.get("remote_url", ""),
                        "branch": repo.get("branch", "main"),
                        "status": "synced",
                    },
                )
                synced += 1
                logger.debug("Synced repo %s", repo_key)
            else:
                skipped += 1

        self.dispatcher.update_worker_state(
            worker_type=WorkerName.LOCAL_REPO_SYNC,
            status=WorkerStatus.IDLE,
            current_task_id="",
        )
        logger.info(
            f"[LocalRepoSyncWorker] Complete: {synced} synced, {skipped} already present."
        )
