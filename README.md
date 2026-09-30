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
| Data | Aerospike Enterprise eval image, namespace `bank` |

## Launch (Docker Compose)

**Prerequisites:** Docker / Docker Compose, and enough RAM for the Aerospike in-memory namespace (default **4G** in `ops/docker/aerospike.conf`).

From the repository root:

```bash
cp .env.example .env   # optional
docker compose up --build -d
docker compose ps
```

| Service | URL / address |
|---|---|
| UI | http://127.0.0.1:3001 |
| API (OpenAPI) | http://127.0.0.1:18000/docs |
| Aerospike | `127.0.0.1:13000` (namespace **`bank`**) |

Compose starts Aerospike, seeds demo data, then brings up the API and UI.

### Try the demo

- **Customer login:** http://127.0.0.1:3001/login — Customer ID `0000001` (after the default 100-customer seed).
- **Admin lab:** choose **Admin** on the login screen (token `admin:admin` by default).

### Useful knobs

Set in `.env` (see `.env.example`):

```bash
SEED_CUSTOMERS=100
SEED_COUNTRY=India
ADMIN_TOKEN=admin:admin
NEXT_PUBLIC_API_BASE=http://127.0.0.1:18000
```

Storage is in-memory — recreating the Aerospike container clears data. Reseed with:

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
