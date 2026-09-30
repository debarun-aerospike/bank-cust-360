# Customer 360 + Admin Load Lab: Entity-Group Plan

## Status

- Phase: **Gate 2 complete**; Gate 3 (cluster + seed) in progress
- Clarification: closed
- Schema guide: approved EG-1–EG-5 + cross-group validation **Passed**
- Schema summary: `docs/modeling/customer-360-schema-summary.md`

## Entity groups

| Group | Scope | Design status | Review checkpoint |
|---|---|---|---|
| EG-1 | Customer master | **Approved** | Passed |
| EG-2 | Accounts + embedded `productDesc` | **Approved** | Passed |
| EG-3 | Booking / balances | **Approved** | Passed |
| EG-4 | Product catalog (ingest SoT) | **Approved** | Passed |
| EG-5 | Inventory counters | **Approved** | Passed |

## Gate sync

| Gate | Status |
|---|---|
| Gate 0 — Plan | Accepted |
| Gate 1 — Clarification | Closed |
| Gate 2 — Schema | **Complete** |
| Gate 3 — Aerospike + seed | **Complete** (`ops/`) |
| Gate 4 — FastAPI backend | **Complete** (`backend/`) |
| Gate 5 — Next.js UI | **Complete** (`frontend/`) |
| Gate 6 — Test hardening | Partial |
