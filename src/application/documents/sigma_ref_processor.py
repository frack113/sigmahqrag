"""Process Sigma rules already in doc_registry and download their reference documents.

This module delegates to :func:`download_sigma_references` with ``mode="registry"``
for the actual download logic. The legacy ``process_sigma_refs`` entry point is
kept for backward compatibility.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from src.application.documents.sigma_ref_downloader import download_sigma_references
from src.shared.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_MAX_WORKERS = 5


def process_sigma_refs(
    db: Any,
    output_dir: str,
    supported_types: set[str] | None = None,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    progress_callback: Callable[[int, int, str], None] | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict[str, Any]:
    """Process Sigma rules already in doc_registry and download their references.

    Delegates to :func:`download_sigma_references` with ``mode="registry"``.

    Parameters
    ----------
    db : DatabaseService
        Database service for writing registry entries.
    output_dir : str
        Directory where downloaded reference files are stored.
    supported_types : set[str] | None
        Allowed content types. Defaults to all reference doc types.
    request_delay : float
        Delay between sequential HEAD requests.
    progress_callback : callable | None
        ``progress_callback(current, total, phase)``.
    max_workers : int
        Max concurrent download threads.

    Returns
    -------
    dict
        Summary with keys: ``total_rules``, ``total_refs``, ``downloaded``,
        ``skipped``, ``failed``.
    """
    if supported_types is None:
        supported_types = SUPPORTED_REFERENCE_DOC_TYPES
    return download_sigma_references(
        db=db,
        output_dir=output_dir,
        mode="registry",
        supported_types=supported_types,
        request_delay=request_delay,
        progress_callback=progress_callback,
        max_workers=max_workers,
    )
