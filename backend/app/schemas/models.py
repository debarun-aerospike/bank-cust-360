from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ProductLine(str, Enum):
    SAVINGS_CURRENT = "SAVINGS_CURRENT"
    TERM_DEPOSIT = "TERM_DEPOSIT"
    LOAN = "LOAN"
    CARD = "CARD"


class CustomerBlock(BaseModel):
    customerId: str
    customerNo: str
    salutation: str
    name: str
    status: str


class AccountRow(BaseModel):
    accountId: str
    productLine: ProductLine
    currency: str = "INR"
    accountStatus: str
    productDescription: str
    balance: float = Field(description="INR amount, 2 decimal places")
    ownership: Literal["PRIMARY", "JOINT"] = "PRIMARY"


class Customer360Response(BaseModel):
    customer: CustomerBlock
    accounts: list[AccountRow]
    accountsByProductLine: dict[str, list[AccountRow]]


class InventoryResponse(BaseModel):
    custCnt: int = 0
    acctCnt: int = 0
    acctS: int = 0
    acctF: int = 0
    acctL: int = 0
    acctC: int = 0
    prodCnt: int = 0
    updatedAt: int | None = None


class LoadState(str, Enum):
    stopped = "stopped"
    running = "running"
    paused = "paused"


class LoadControlRequest(BaseModel):
    action: Literal["start", "stop", "pause", "resume", "set"]
    targetReadTps: int | None = Field(default=None, ge=0, le=5000)
    targetWriteTps: int | None = Field(default=None, ge=0, le=5000)


class LoadStatusResponse(BaseModel):
    state: LoadState
    targetReadTps: int
    targetWriteTps: int
    achievedReadTps: float
    achievedWriteTps: float
    errorRate: float
    latencyMs: dict[str, float]
    seededCustomerMax: int


class IngestRequest(BaseModel):
    targetCustomerCount: int = Field(ge=1, le=9_999_999)
    checkpointEvery: int = Field(default=1000, ge=100)
    country: str = Field(default="India", min_length=1, max_length=64)


class IngestStatusResponse(BaseModel):
    state: Literal["idle", "running", "failed", "completed"]
    targetCustomerCount: int | None = None
    country: str | None = None
    message: str | None = None
    lastExitCode: int | None = None


class MetricsBucket(BaseModel):
    ts: int
    readTps: float
    writeTps: float
    errorRate: float
    latencyMs: dict[str, float]
    targetReadTps: int
    targetWriteTps: int


class HealthResponse(BaseModel):
    status: str
    aerospike: bool
    loadState: LoadState
    details: dict[str, Any] = Field(default_factory=dict)
