# Gate 4 — FastAPI Customer 360 + Admin load lab

Uses **uv** for all Python dependency and run commands.

For the full stack in Docker (Aerospike + seed + API + UI), from the repo root:

```bash
docker compose up --build -d
```

See `ops/README.md`.

## Prerequisites

- Aerospike lab running (`ops/docker` or root `docker compose`) with seed data (`ops/seed`)
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
cd backend
uv sync --group dev
```

Environment (optional `.env`, or `AEROSPIKE_CONFIG_FILE`):

| Variable | Default | Meaning |
|---|---|---|
| `AEROSPIKE_HOSTS` | _(empty)_ | Comma-separated seeds `host` or `host:port` (preferred) |
| `AEROSPIKE_HOST` | `127.0.0.1` | Single seed when `AEROSPIKE_HOSTS` is empty |
| `AEROSPIKE_PORT` | `13000` | Default port for hosts without an explicit port |
| `AEROSPIKE_NAMESPACE` | `bank` | |
| `AEROSPIKE_USER` | _(empty)_ | Optional DB user |
| `AEROSPIKE_PASSWORD` | _(empty)_ | Optional DB password |
| `ADMIN_TOKEN` | `admin:admin` | Bearer token for Admin APIs |
| `SEEDED_CUSTOMER_MAX` | `100` | Loadgen ID range (updated after ingest) |

## Run

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI: http://127.0.0.1:8000/docs

## Auth

- Customer 360: `Authorization: Bearer mock:0000001`
- Admin: `Authorization: Bearer admin:admin`
- Metrics WebSocket: `ws://127.0.0.1:8000/api/v1/admin/metrics/stream?token=admin:admin`

## Example calls

```bash
# Customer 360
curl -s -H 'Authorization: Bearer mock:0000001' \
  http://127.0.0.1:8000/api/v1/customers/0000001/360 | jq .

# Inventory
curl -s -H 'Authorization: Bearer admin:admin' \
  http://127.0.0.1:8000/api/v1/admin/inventory | jq .

# Start load
curl -s -X PUT -H 'Authorization: Bearer admin:admin' -H 'Content-Type: application/json' \
  -d '{"action":"start","targetReadTps":50,"targetWriteTps":10}' \
  http://127.0.0.1:8000/api/v1/admin/load | jq .

# Stop load (kill-switch)
curl -s -X PUT -H 'Authorization: Bearer admin:admin' -H 'Content-Type: application/json' \
  -d '{"action":"stop"}' \
  http://127.0.0.1:8000/api/v1/admin/load | jq .

# Ingestion simulation
curl -s -X POST -H 'Authorization: Bearer admin:admin' -H 'Content-Type: application/json' \
  -d '{"targetCustomerCount":100,"checkpointEvery":50}' \
  http://127.0.0.1:8000/api/v1/admin/ingest | jq .
```

## Tests

```bash
uv run pytest -q
```
