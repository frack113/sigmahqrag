"""API endpoints for GitHub release tag listing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.shared.release_selector import create_release_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/releases", tags=["v1-releases"])


@router.get("/{service}")
async def list_service_releases(service: str):
    """List available releases for a known service.

    Known services are registered in SERVICE_REPOS_EXTENDED
    (llama.cpp, qdrant, qdrant-web-ui).
    """
    selector = create_release_selector()
    try:
        releases = await selector.get_service_releases(service)
        return JSONResponse(content={"service": service, "releases": releases})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Failed to list releases for {service}: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to fetch releases: {e}"},
        )


@router.get("/custom/")
async def list_custom_releases(
    owner: str = Query(..., description="GitHub owner"),
    repo: str = Query(..., description="Repository name"),
):
    """List available releases for an arbitrary GitHub repository."""
    selector = create_release_selector()
    try:
        releases = await selector.get_custom_releases(owner, repo)
        return JSONResponse(content={"owner": owner, "repo": repo, "releases": releases})
    except Exception as e:
        logger.error(f"Failed to list releases for {owner}/{repo}: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": f"Failed to fetch releases: {e}"},
        )
