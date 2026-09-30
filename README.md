# Customer 360

Retail-bank **Customer 360** lab on Aerospike: a netbanking-style accounts home plus an Admin load lab for live throughput and latency.

## Project goal

Demonstrate an access-pattern–driven Aerospike data model and a thin full-stack demo around it:

1. **Customer 360 (netbanking view)** — Sign in with a Customer ID and see profile details plus linked accounts (Savings/Current, Term Deposits, Loans, Cards) with product description and computed booking balance in one assembled response.
2. **Admin load lab** — Inspect inventory counters, start/pause/resume/stop configurable read/write TPS against the seeded dataset, and watch live app-side latency and throughput charts.

Schema design lives under `docs/modeling/`. Application code is intentionally a lab around that model (FastAPI + Next.js + Aerospike).

## Stack

| Layer | Tech |
|---|---|
| UI | Next.js (`frontend/`) |
| API + load workers | FastAPI (`backend/`) |
| Data | Aerospike (bundled Docker lab **or** your external cluster), namespace `bank` |

## Launch (Docker Compose)

**Prerequisites:** Docker / Docker Compose. For the bundled DB, enough RAM for the in-memory namespace (default **4G** in `ops/docker/aerospike.conf`).

```bash
cp .env.example .env   # optional — edit for external clusters / auth
```

### Option A — everything in Docker (default)

```bash
docker compose up --build -d
docker compose ps
```

| Service | URL / address |
|---|---|
| UI | http://127.0.0.1:4000 |
| API (OpenAPI) | http://127.0.0.1:18000/docs |
| Aerospike | `127.0.0.1:13000` (namespace **`bank`**) |

Compose starts Aerospike, seeds demo data, then brings up the API and UI.

### Option B — external Aerospike cluster

1. Put seed IPs (and optional DB credentials) in `.env`:

```bash
AEROSPIKE_HOSTS=10.0.0.11:3000,10.0.0.12:3000
AEROSPIKE_NAMESPACE=bank
AEROSPIKE_USER=app_user          # optional
AEROSPIKE_PASSWORD=secret        # optional
# Or load the same keys from a file the API also reads:
# AEROSPIKE_CONFIG_FILE=./ops/aerospike.client.env
```

2. Start API + UI **without** the bundled DB:

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml up --build -d
```

3. Seed the external cluster once (namespace `bank` must already exist there):

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml run --rm --no-deps seed \
  --hosts="$AEROSPIKE_HOSTS" \
  --customers=100 \
  --country=India
```

Native seed (without Docker) accepts the same env vars / `--hosts` / `--user` / `--password` — see `ops/README.md`.

### Try the demo

- **Customer login:** http://127.0.0.1:4000/login — Customer ID `0000001` (after the default 100-customer seed).
- **Admin lab:** choose **Admin** on the login screen (token `admin:admin` by default).

### Connection settings

| Variable | Purpose |
|---|---|
| `AEROSPIKE_HOSTS` | Comma-separated seeds: `host` or `host:port` |
| `AEROSPIKE_HOST` / `AEROSPIKE_PORT` | Legacy single-seed fallback when `AEROSPIKE_HOSTS` is empty |
| `AEROSPIKE_NAMESPACE` | Namespace (default `bank`) |
| `AEROSPIKE_USER` / `AEROSPIKE_PASSWORD` | Optional database user (security-enabled / EE clusters) |
| `AEROSPIKE_CONFIG_FILE` | Optional extra env file for the API (`ops/aerospike.client.env.example`) |

The API and Admin ingest use the same settings.

Bundled Aerospike storage is in-memory — recreating that container clears data. Reseed with:

```bash
docker compose run --rm seed
```

Stop everything:

```bash
docker compose down
```

## More detail

- Ops, native seed, and Aerospike-only bring-up: [`ops/README.md`](ops/README.md)
- Backend (local `uv` run): [`backend/README.md`](backend/README.md)
- Frontend (local `npm` run): [`frontend/README.md`](frontend/README.md)
- Approved schema: [`docs/modeling/customer-360-schema-guide.md`](docs/modeling/customer-360-schema-guide.md)
