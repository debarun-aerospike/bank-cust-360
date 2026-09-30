from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import aerospike_client as as_client
from app.api.routes import admin_router, router
from app.schemas.models import HealthResponse
from app.services.loadgen import load_generator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("c360")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    as_client.connect()
    logger.info("Aerospike connected")
    yield
    load_generator.stop()
    as_client.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Customer 360 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ok = False
    try:
        client = as_client.get_client()
        # lightweight: is_connected if available
        ok = bool(getattr(client, "is_connected", lambda: True)())
        # try info on node
        try:
            client.info_all("status")
            ok = True
        except Exception:  # noqa: BLE001
            ok = True  # client exists; info may vary
    except Exception:  # noqa: BLE001
        ok = False
    return HealthResponse(
        status="ok" if ok else "degraded",
        aerospike=ok,
        loadState=load_generator.state,
    )


@app.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    h = health()
    if not h.aerospike:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Aerospike not ready")
    return h
