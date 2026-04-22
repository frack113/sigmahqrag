"""Statistics collection utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "sigma_rules"


@dataclass(frozen=True)
class IndexStats:
    """Statistics for indexed rules."""

    total_count: int
    by_status: dict[str, int]
    by_level: dict[str, int]
    by_tactic: dict[str, int]


class StatsCollector:
    """Collect statistics from indexed data."""

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
    ) -> None:
        """Initialize stats collector.

        Args:
            collection_name: Qdrant collection name
        """
        self.collection_name = collection_name

    async def get_stats(self) -> IndexStats:
        """Get indexing statistics.

        Returns:
            IndexStats with counts and breakdowns
        """
        try:
            service = QdrantService(
                collection_name=self.collection_name,
                vector_size=384,
            )

            is_healthy = await service.health_check()
            if not is_healthy:
                return IndexStats(
                    total_count=0,
                    by_status={},
                    by_level={},
                    by_tactic={},
                )

            total_count = await service.get_collection_count()

            by_status = await self._get_grouped_counts(service, "status")
            by_level = await self._get_grouped_counts(service, "level")
            by_tactic = await self._get_grouped_counts(service, "tactic")

            return IndexStats(
                total_count=total_count,
                by_status=by_status,
                by_level=by_level,
                by_tactic=by_tactic,
            )

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return IndexStats(
                total_count=0,
                by_status={},
                by_level={},
                by_tactic={},
            )

    async def _get_grouped_counts(
        self,
        service: QdrantService,
        field: str,
    ) -> dict[str, int]:
        """Get grouped counts for a field.

        Args:
            service: QdrantService instance
            field: Metadata field to group by

        Returns:
            Dict mapping field values to counts
        """
        try:
            counts: dict[str, int] = {}
            offset = None
            batch_size = 1000

            while True:
                results = await service.scroll_with_filter(
                    filter_=None,
                    limit=batch_size,
                    offset=offset,
                )

                if not results:
                    break

                for result in results:
                    metadata = result.get("metadata", {})
                    value = metadata.get(field, "unknown")

                    if value:
                        counts[value] = counts.get(value, 0) + 1

                if len(results) < batch_size:
                    break

                offset = results[-1].get("id")

            return counts

        except Exception as e:
            logger.warning(f"Failed to get grouped counts for {field}: {e}")
            return {}

    def format_stats(self, stats: IndexStats) -> str:
        """Format stats as markdown.

        Args:
            stats: IndexStats to format

        Returns:
            Formatted markdown string
        """
        lines = [
            f"**Total Rules:** {stats.total_count}",
        ]

        if stats.by_status:
            lines.append("\n**By Status:**")
            for status, count in sorted(stats.by_status.items()):
                lines.append(f"- {status}: {count}")

        if stats.by_level:
            lines.append("\n**By Level:**")
            for level, count in sorted(stats.by_level.items()):
                lines.append(f"- {level}: {count}")

        if stats.by_tactic:
            lines.append("\n**By Tactic:**")
            for tactic, count in sorted(stats.by_tactic.items()):
                lines.append(f"- {tactic}: {count}")

        return "\n".join(lines)


def create_stats_collector(collection_name: str = DEFAULT_COLLECTION) -> StatsCollector:
    """Create a stats collector.

    Args:
        collection_name: Qdrant collection name

    Returns:
        StatsCollector instance
    """
    return StatsCollector(collection_name)
