from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from ..db import get_connection, metrics
from ..serialize import df_to_records

router = APIRouter(prefix="/funnel", tags=["funnel"])


@router.get("/onboarding")
def onboarding_funnel(con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    return df_to_records(metrics.onboarding_funnel(con))


@router.get("/time-to-activation")
def time_to_activation(con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    records = df_to_records(metrics.time_to_activation(con))
    return records[0] if records else {}
