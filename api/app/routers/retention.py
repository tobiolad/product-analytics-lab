from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, Query

from ..db import get_connection, metrics
from ..serialize import df_to_records

router = APIRouter(prefix="/retention", tags=["retention"])


@router.get("/cohorts")
def cohort_retention(
    max_weeks: int = Query(6, ge=1, le=26),
    con: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    return df_to_records(metrics.cohort_retention(con, max_weeks=max_weeks))
