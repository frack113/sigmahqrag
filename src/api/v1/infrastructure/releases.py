"""API endpoints for GitHub release tag listing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.infrastructure.database import DatabaseService
from src.shared.release_selector import SERVICE_REPOS_EXTENDED, create_release_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/releases", tags=["v1-releases"])


@router.get("/status/timestamps")
async def get_release_timestamps():
    """Return fetched_at timestamps for all cached services."""
    try:
        db = DatabaseService.get_instance()
        timestamps = db.get_release_cache_timestamps()
        return JSONResponse(content={"timestamps": timestamps})
    except Exception as e:
        logger.error(f"Failed to read release timestamps: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/all-releases")
async def get_all_releases():
    """Return all cached releases for display in UI."""
    try:
        db = DatabaseService.get_instance()
        with db._lock:
            conn = db._get_reader_connection()
            if conn is None:
                return JSONResponse(content={"releases": []})

            rows = conn.execute("""
                SELECT 
                    service, 
                    json_extract(data, '$[0].tag_name') as last_tag_name,
                    json_extract(data, '$[0].published_at') as published_at,
                    fetched_at
                FROM release_cache
                WHERE data IS NOT NULL AND json_extract(data, '$[0].tag_name') IS NOT NULL
            """).fetchall()

        releases = []
        for row in rows:
            releases.append(
                {
                    "service": row[0],
                    "last_tag_name": row[1],
                    "published_at": row[2],
                    "fetched_at": row[3],
                }
            )

        return JSONResponse(content={"releases": releases})
    except Exception as e:
        logger.error(f"Failed to read all releases: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/custom/")
async def list_custom_releases(
    owner: str = Query(..., description="GitHub owner"),
    repo: str = Query(..., description="Repository name"),
):
    """Read cached releases for an arbitrary GitHub repo from DuckDB."""
    service_key = f"{owner}/{repo}"
    try:
        db = DatabaseService.get_instance()
        releases = db.get_release_cache(service_key)
        return JSONResponse(content={"owner": owner, "repo": repo, "releases": releases})
    except Exception as e:
        logger.error(f"Failed to read release cache for {owner}/{repo}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/refresh")
async def refresh_all_releases():
    """Fetch releases for all registered services from GitHub and cache in DuckDB.

    Stores each service's releases in DuckDB, persists, and returns all data.
    """
    selector = create_release_selector()
    db = DatabaseService.get_instance()
    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    for service in SERVICE_REPOS_EXTENDED:
        try:
            releases = await selector.get_service_releases(service)
            db.set_release_cache(service, releases)
            results[service] = releases
        except Exception as e:
            logger.error(f"Failed to refresh releases for {service}: {e}")
            errors[service] = str(e)

    try:
        db.persist()
    except Exception as e:
        logger.error(f"Failed to persist release cache: {e}")

    return JSONResponse(content={"services": results, "errors": errors or None})


@router.get("/{service}")
async def list_service_releases(service: str):
    """Read cached releases for a known service from DuckDB.

    Known services are registered in SERVICE_REPOS_EXTENDED
    (llama.cpp, qdrant, qdrant-web-ui).
    Returns releases or null if not cached.
    """
    if service not in SERVICE_REPOS_EXTENDED:
        known = list(SERVICE_REPOS_EXTENDED)
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown service '{service}'. Known: {', '.join(known)}"},
        )
    try:
        db = DatabaseService.get_instance()
        releases = db.get_release_cache(service)
        return JSONResponse(content={"service": service, "releases": releases})
    except Exception as e:
        logger.error(f"Failed to read release cache for {service}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
