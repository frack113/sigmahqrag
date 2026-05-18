import asyncio
import logging
from pathlib import Path

from llama_index.core.schema import Document

from src.back.worker.base import BaseWorker
from src.back.rag.ingestion import IngestionPipelineBuilder

logger = logging.getLogger(__name__)


class SigmaRefEmbeddingWorker(BaseWorker):
    """Embeds Sigma Reference documents from doc_sigma_ref into Qdrant."""

    async def process(self, task: dict) -> None:
        task_id = task["task_id"]
        collection_name = task.get("collection_name", "sigmaref")
        registry_path = Path(task.get("registry_path", "data/documents/sigmaref"))

        logger.info(f"[SigmaRefEmbeddingWorker] Embedding SigmaRef docs into {collection_name}")

        raw_entries = self.db.get_doc_sigma_ref()
        if not raw_entries:
            logger.info("[SigmaRefEmbeddingWorker] No entries in doc_sigma_ref, nothing to embed")
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="completed",
                source_type="sigmaref_embeddings",
                total=0,
                processed=0,
                collection_name=collection_name,
                progress_percent=100.0,
            )
            return

        registry_entries = []
        for e in raw_entries:
            registry_entries.append(
                {
                    "hash": e.get("url_hash", ""),
                    "file_name": f"{e.get('url_hash', '')}.md",
                    "path": f"{e.get('url_hash', '')}.md",
                    **{k: v for k, v in e.items() if k not in ("url_hash",)},
                }
            )

        total = len(registry_entries)
        errors = []
        skipped = []

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="running",
            source_type="sigmaref_embeddings",
            total=total,
            processed=0,
            collection_name=collection_name,
            progress_percent=0.0,
        )

        builder = IngestionPipelineBuilder(collection_name=collection_name)

        for idx, entry in enumerate(registry_entries):
            file_hash = entry.get("hash", entry.get("id", ""))
            file_name = entry.get("file_name", "")

            file_path = None
            for candidate in (registry_path / file_name, registry_path / file_hash):
                if candidate.exists():
                    file_path = candidate
                    break
            if file_path is None:
                matches = sorted(registry_path.glob(f"{file_hash}.*"))
                file_path = matches[0] if matches else registry_path / f"{file_hash}.md"

            processed = idx + 1
            current_file = file_name or file_hash
            percent = (processed / total) * 100

            self.db.upsert_embed_progress(
                task_id=task_id,
                status="running",
                source_type="sigmaref_embeddings",
                total=total,
                processed=processed,
                current_file=current_file,
                collection_name=collection_name,
                progress_percent=percent,
            )

            doc_text = ""
            try:
                doc_text = file_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                logger.warning(f"[SigmaRefEmbeddingWorker] File not found: {file_path}")
                skipped.append(current_file)
                continue
            except Exception as e:
                logger.warning(f"[SigmaRefEmbeddingWorker] Error reading {file_path}: {e}")
                errors.append({"file": current_file, "error": str(e)})
                continue

            metadata = dict(entry)
            metadata.pop("hash", None)
            metadata["source"] = "sigmaref"
            metadata["collection"] = collection_name

            doc = Document(text=doc_text, metadata=metadata)
            try:
                builder.run(documents=[doc])
            except Exception as e:
                logger.error(f"[SigmaRefEmbeddingWorker] Error embedding {current_file}: {e}")
                errors.append({"file": current_file, "error": str(e)})

            await asyncio.sleep(0)

        processed = total - len(errors) - len(skipped)
        error_summary = f"{len(errors)} errors, {len(skipped)} skipped" if errors or skipped else ""

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="completed",
            source_type="sigmaref_embeddings",
            total=total,
            processed=processed,
            skipped=len(skipped),
            errors=error_summary,
            collection_name=collection_name,
            progress_percent=100.0,
        )

        logger.info(
            f"[SigmaRefEmbeddingWorker] Complete: {processed}/{total} embedded, "
            f"{len(errors)} errors, {len(skipped)} skipped"
        )
