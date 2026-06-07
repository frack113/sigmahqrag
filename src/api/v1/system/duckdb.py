from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import get_database_service
from src.infrastructure.database import DatabaseService

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
