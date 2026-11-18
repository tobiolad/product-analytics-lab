from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from ..db import get_connection, metrics
from ..serialize import df_to_records

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/adoption")
def feature_adoption(con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    return df_to_records(metrics.feature_adoption(con))
