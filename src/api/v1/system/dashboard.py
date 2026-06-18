from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import get_database_service
from src.application.system.duckdb import DuckDbManager
from src.infrastructure.database import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


class TableListResponse(BaseModel):
    tables: list[str]


class TableDataResponse(BaseModel):
    table: str
    rows: list[dict]
    total: int
    limit: int
    offset: int


class DashboardResponse(BaseModel):
    health: dict
    tables: list[dict]
    config: dict
    workers: list[dict]
    recent_errors: list[dict]


@router.get("", response_model=DashboardResponse)
async def dashboard(db: DatabaseService = Depends(get_database_service)):
    manager = DuckDbManager.default()
    health = manager.status()

    tables = []
    for t in db.get_tables():
        try:
            count = db.get_table_count(t)
        except Exception:
            count = 0
        tables.append({"name": t, "row_count": count})

    config_keys = {}
    for key in ("schema_version", "app_version", "theme", "backend", "logging"):
        try:
            val = db.get_config(key)
            if val is not None:
                config_keys[key] = val
        except Exception:
            pass

    try:
        workers = db.get_all_workers()
    except Exception:
        workers = []

    try:
        recent_errors = db.get_doc_errors(limit=10)
    except Exception:
        recent_errors = []

    return DashboardResponse(
        health=health,
        tables=tables,
        config=config_keys,
        workers=workers,
        recent_errors=recent_errors,
    )


@router.get("/tables", response_model=TableListResponse)
async def list_tables(db: DatabaseService = Depends(get_database_service)):
    return TableListResponse(tables=db.get_tables())


@router.get("/tables/{table_name}", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: DatabaseService = Depends(get_database_service),
):
    try:
        data = db.get_table_data(table_name, limit=limit, offset=offset)
        total = db.get_table_count(table_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    return TableDataResponse(table=table_name, rows=data, total=total, limit=limit, offset=offset)
