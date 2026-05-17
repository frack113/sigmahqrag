from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.back.database import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/duckdb", tags=["duckdb"])


class TableListResponse(BaseModel):
    tables: list[str]


class TableDataResponse(BaseModel):
    table: str
    rows: list[dict]
    total: int
    limit: int
    offset: int


def _get_db() -> DatabaseService:
    try:
        return DatabaseService.get_instance()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database not initialized")


@router.get("/tables", response_model=TableListResponse)
async def list_tables():
    db = _get_db()
    return TableListResponse(tables=db.get_tables())


@router.get("/tables/{table_name}", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    db = _get_db()
    try:
        data = db.get_table_data(table_name, limit=limit, offset=offset)
        total = db.get_table_count(table_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    return TableDataResponse(table=table_name, rows=data, total=total, limit=limit, offset=offset)
