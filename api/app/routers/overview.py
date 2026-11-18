from __future__ import annotations

from typing import Literal, Optional

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import get_connection, metrics
from ..serialize import df_to_records

router = APIRouter(prefix="/overview", tags=["overview"])

# account_activation / accounts columns safe to GROUP BY -- metrics.activation_rate
# interpolates `by` directly into SQL, so it must be checked against a fixed
# allowlist here rather than passed through from the query string unchecked.
ACTIVATION_GROUP_COLUMNS = {"acquisition_channel", "plan_id"}


@router.get("/signup-trend")
def signup_trend(
    granularity: Literal["day", "week"] = Query("week"),
    con: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    return df_to_records(metrics.signup_trend(con, granularity=granularity))


@router.get("/activation-rate")
def activation_rate(
    by: Optional[str] = Query(None, description="Group by 'acquisition_channel' or 'plan_id'"),
    con: duckdb.DuckDBPyConnection = Depends(get_connection),
):
    if by is not None and by not in ACTIVATION_GROUP_COLUMNS:
        raise HTTPException(status_code=400, detail=f"'by' must be one of {sorted(ACTIVATION_GROUP_COLUMNS)}")
    return df_to_records(metrics.activation_rate(con, by=by))


@router.get("/dau-wau")
def dau_wau(con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    return df_to_records(metrics.dau_wau(con))


@router.get("/conversion")
def conversion_by_channel_and_plan(con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    return df_to_records(metrics.conversion_by_channel_and_plan(con))
