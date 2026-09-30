from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.auth import require_admin, require_mock_customer
from app.repositories import aerospike_repo as repo
from app.schemas.models import (
    Customer360Response,
    IngestRequest,
    IngestStatusResponse,
    InventoryResponse,
    LoadControlRequest,
    LoadStatusResponse,
)
from app.services import customer360
from app.services.ingest import ingest_job
from app.services.loadgen import load_generator
from app.services.metrics import metrics_hub

router = APIRouter()
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/customers/{customer_id}/360", response_model=Customer360Response)
def get_customer_360(
    customer_id: str,
    account_status: str | None = Query(default="Active"),
    auth_customer: str = Depends(require_mock_customer),
) -> Customer360Response:
    if customer_id != auth_customer:
        raise HTTPException(status_code=403, detail="Token customer mismatch")
    if len(customer_id) != 7 or not customer_id.isdigit():
        raise HTTPException(status_code=422, detail="Customer ID must be 7 digits")
    try:
        return customer360.assemble_customer_360(
            customer_id,
            status_filter=None if account_status in ("*", "ALL", "") else account_status,
            require_active_customer=True,
        )
    except customer360.IneligibleCustomerError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except repo.NotFoundError:
        raise HTTPException(status_code=404, detail="Customer not found") from None


@admin_router.get("/inventory", response_model=InventoryResponse)
def admin_inventory(_: None = Depends(require_admin)) -> InventoryResponse:
    bins = repo.get_inventory()
    return InventoryResponse(
        custCnt=int(bins.get("custCnt") or 0),
        acctCnt=int(bins.get("acctCnt") or 0),
        acctS=int(bins.get("acctS") or 0),
        acctF=int(bins.get("acctF") or 0),
        acctL=int(bins.get("acctL") or 0),
        acctC=int(bins.get("acctC") or 0),
        prodCnt=int(bins.get("prodCnt") or 0),
        updatedAt=bins.get("updatedAt"),
    )


@admin_router.get("/load", response_model=LoadStatusResponse)
def admin_load_get(_: None = Depends(require_admin)) -> LoadStatusResponse:
    return LoadStatusResponse(**load_generator.status())


@admin_router.put("/load", response_model=LoadStatusResponse)
def admin_load_put(body: LoadControlRequest, _: None = Depends(require_admin)) -> LoadStatusResponse:
    load_generator.configure(body.targetReadTps, body.targetWriteTps)
    if body.action == "start":
        if load_generator.target_read_tps == 0 and load_generator.target_write_tps == 0:
            raise HTTPException(status_code=422, detail="Set targetReadTps and/or targetWriteTps before start")
        load_generator.start()
    elif body.action == "stop":
        load_generator.stop()
    elif body.action == "pause":
        load_generator.pause()
    elif body.action == "resume":
        load_generator.resume()
    elif body.action == "set":
        pass
    return LoadStatusResponse(**load_generator.status())


@admin_router.post("/ingest", response_model=IngestStatusResponse)
def admin_ingest_start(body: IngestRequest, _: None = Depends(require_admin)) -> IngestStatusResponse:
    try:
        ingest_job.start(body.targetCustomerCount, body.checkpointEvery, body.country)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IngestStatusResponse(**ingest_job.status())


@admin_router.get("/ingest", response_model=IngestStatusResponse)
def admin_ingest_status(_: None = Depends(require_admin)) -> IngestStatusResponse:
    return IngestStatusResponse(**ingest_job.status())


@admin_router.websocket("/metrics/stream")
async def admin_metrics_stream(websocket: WebSocket) -> None:
    # Simple token via query for WS (browsers cannot set Authorization easily)
    token = websocket.query_params.get("token")
    from app.config import get_settings

    if token != get_settings().admin_token:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    try:
        while True:
            snap = metrics_hub.snapshot()
            await websocket.send_text(json.dumps(snap))
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
