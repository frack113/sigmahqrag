import hashlib
import logging
from datetime import datetime
from pathlib import Path
from src.back.worker.base import BaseWorker
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP

logger = logging.getLogger(__name__)

class FileDiscoveryWorker(BaseWorker):
    """Specialized worker for file discovery tasks."""
    async def process(self, task: dict) -> None:
        task_id = task['task_id']
        source_type = task.get('source_type', 'unknown')
        collection_name = task['collection_name']
        
        if source_type == 'local':
            base_path = Path(task_id) 
        else: # github
            parts = collection_name.split('/')
            if len(parts) == 2:
                base_path = Path("data/github") / parts[0] / parts[1]
            else:
                raise ValueError(f"Invalid collection name for github discovery: {collection_name}")

        if not base_path.exists():
            raise FileNotFoundError(f"Path does not exist: {base_path}")

        # Determine org/repo for doc_registry
        org = ""
        repo = ""
        if source_type == 'github':
            parts = collection_name.split('/')
            if len(parts) == 2:
                org = parts[0]
                repo = parts[1]

        # Check for selected directories in DuckDB
        selected_dirs = []
        if source_type == 'github':
            try:
                selected_dirs = self.db.get_selected_dirs(collection_name)
                logger.info(f"[FileDiscoveryWorker] Repository {collection_name} has {len(selected_dirs)} selected directories.")
            except Exception as e:
                logger.error(f"[FileDiscoveryWorker] Error fetching selected dirs for {collection_name}: {e}")

        logger.info(f"Starting file discovery in {base_path}")
        
        files_to_process = []
        for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
            pattern = f"**/*.{ext}"
            for found_file in base_path.glob(pattern):
                # If selected_dirs is not empty, the file must be within one of them
                if selected_dirs:
                    rel_to_repo = found_file.relative_to(base_path).as_posix()
                    if any(rel_to_repo.startswith(sd.lstrip('./')) for sd in selected_dirs):
                        files_to_process.append(found_file)
                else:
                    # No restrictions, add everything
                    files_to_process.append(found_file)

        total_files = len(files_to_process)
        processed_count = 0
        skipped_count = 0

        for file_path in files_to_process:
            try:
                file_rel_path = file_path.relative_to(base_path).as_posix()
                processed_count += 1
                percent = (processed_count / total_files) * 100 if total_files > 0 else 100

                # Compute hash for doc_registry
                try:
                    file_bytes = file_path.read_bytes()
                    content_hash = hashlib.sha256(file_bytes).hexdigest()
                    file_size = file_path.stat().st_size
                except Exception:
                    content_hash = ""
                    file_size = 0

                # Support both 'rules' and 'specification' as content_type
                content_type = ""
                if source_type == 'local':
                    content_type = "local"
                else:
                    # Determine content type from the path
                    rel_lower = file_rel_path.lower()
                    if rel_lower.startswith("rules") or "/rules/" in rel_lower:
                        content_type = "rules"
                    elif rel_lower.startswith("specification") or "/specification/" in rel_lower:
                        content_type = "specification"
                    else:
                        content_type = ext

                # Upsert into doc_registry
                self.db.upsert_doc_registry({
                    "org": org,
                    "repo": repo,
                    "content_type": content_type,
                    "file_name": file_rel_path,
                    "content_hash": content_hash,
                    "file_size": file_size,
                    "last_seen": datetime.now().isoformat(),
                    "status": "discovered",
                })

                self.db.upsert_embed_progress(
                    task_id=task_id,
                    status='running',
                    total=total_files,
                    processed=processed_count,
                    skipped=skipped_count,
                    current_file=file_rel_path,
                    collection_name=collection_name,
                    progress_percent=percent
                )
            except Exception as e:
                logger.error(f"[FileDiscoveryWorker] Error processing file {file_path}: {e}")
                skipped_count += 1

        self.db.upsert_embed_progress(
            task_id=task_id,
            status='completed',
            total=total_files,
            processed=processed_count,
            skipped=skipped_count,
            progress_percent=100.0,
            collection_name=collection_name
        )
