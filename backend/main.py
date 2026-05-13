"""FastAPI entry point.

Run:
    uvicorn main:app --reload --port 8000

The frontend's vite.config.ts proxies `/api/*` here.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.neo4j_client import close as close_driver, settings
from llm import anchor_cache
from middleware.observability import ObservabilityMiddleware, metrics_store
from routes.graph import router as graph_router
from routes.rank import router as rank_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await anchor_cache.warm()
    yield
    close_driver()


app = FastAPI(title="Semantica", version="0.1.0", lifespan=lifespan)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings().allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph_router)
app.include_router(rank_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metrics")
def get_metrics() -> dict:
    return metrics_store.summary()
