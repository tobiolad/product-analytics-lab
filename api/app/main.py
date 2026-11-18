"""
Read-only analytics API over the DuckDB database built by `db/load.py`.
Every route delegates to db/metrics.py or db/experiment.py -- this file
only wires up HTTP, it holds no analysis logic of its own.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import experiments, features, funnel, overview, retention

app = FastAPI(
    title="Product Analytics Lab API",
    description="Read-only analytics over synthetic SaaS product usage and A/B experiment data.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(funnel.router)
app.include_router(retention.router)
app.include_router(features.router)
app.include_router(experiments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
