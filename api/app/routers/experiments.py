from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_connection, experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("")
def list_experiments(con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    rows = con.execute(
        """
        SELECT experiment_name, COUNT(*) AS assigned_users, MIN(assigned_at) AS first_assigned, MAX(assigned_at) AS last_assigned
        FROM experiment_assignments
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()
    return [
        {"experiment_name": r[0], "assigned_users": r[1], "first_assigned": str(r[2]), "last_assigned": str(r[3])}
        for r in rows
    ]


@router.get("/{experiment_name}/analysis")
def analyze_experiment(experiment_name: str, con: duckdb.DuckDBPyConnection = Depends(get_connection)):
    known = {
        r[0] for r in con.execute("SELECT DISTINCT experiment_name FROM experiment_assignments").fetchall()
    }
    if experiment_name not in known:
        raise HTTPException(status_code=404, detail=f"No such experiment '{experiment_name}'. Known: {sorted(known)}")
    return experiment.run_experiment_analysis(con, experiment_name)
