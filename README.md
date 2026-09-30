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
| Data | Aerospike — either the **bundled Docker lab** or an **external cluster**, namespace `bank` |

## Prerequisites

- Docker and Docker Compose
- For the bundled Aerospike lab: enough RAM for the in-memory namespace (default **4G** in `ops/docker/aerospike.conf`)
- For an external cluster: network reachability to every node (not only the seed hosts), and a namespace named **`bank`** already configured on that cluster

```bash
cp .env.example .env
```

Edit `.env` when you use an external cluster or want to change seed size, country, or admin token.

---

## Option A — launch everything in Docker

This starts Aerospike, loads demo data, then brings up the API and UI.

```bash
docker compose up --build -d
docker compose ps
```

| Service | URL / address |
|---|---|
| UI | http://127.0.0.1:4000 |
| API (OpenAPI) | http://127.0.0.1:18000/docs |
| Aerospike | `127.0.0.1:13000` (namespace **`bank`**) |

Inside Compose, the API connects to `aerospike:3000` on the Docker network automatically.

**Reseed** (bundled DB is in-memory; recreate clears data):

```bash
docker compose run --rm seed
```

**Stop:**

```bash
docker compose down
```

---

## Option B — use an external Aerospike cluster

Run only the API and UI in Docker; point them at your existing cluster.

### 1. Configure connection in `.env`

```bash
AEROSPIKE_HOSTS=10.0.0.11:3000,10.0.0.12:3000
AEROSPIKE_NAMESPACE=bank
AEROSPIKE_USER=app_user          # optional — security-enabled / EE clusters
AEROSPIKE_PASSWORD=secret        # optional
```

Each `AEROSPIKE_HOSTS` entry is `host` or `host:port`.  
Optional: put the same keys in a separate file and set:

```bash
AEROSPIKE_CONFIG_FILE=./ops/aerospike.client.env
```

(see `ops/aerospike.client.env.example`).

### 2. Start API + UI (no bundled Aerospike)

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.external.yml ps
```

| Service | URL / address |
|---|---|
| UI | http://127.0.0.1:4000 |
| API (OpenAPI) | http://127.0.0.1:18000/docs |
| Aerospike | your cluster (`AEROSPIKE_HOSTS`) |

Compose will fail fast if `AEROSPIKE_HOSTS` is not set.

### 3. Seed the external cluster once

Namespace **`bank`** must already exist on the cluster.

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml run --rm --no-deps seed \
  --hosts="$AEROSPIKE_HOSTS" \
  --customers=100 \
  --country=India
```

If the cluster requires auth, either export `AEROSPIKE_USER` / `AEROSPIKE_PASSWORD` or pass `--user` / `--password`.

**Native seed** (without Docker) works the same:

```bash
cd ops/seed
uv sync
uv run python seed.py \
  --hosts=10.0.0.11:3000,10.0.0.12:3000 \
  --customers=100 \
  --country=India
```

### 4. Stop

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml down
```

---

## Try the demo

After either launch path (and a successful seed):

- **Customer login:** http://127.0.0.1:4000/login — Customer ID `0000001`
- **Admin lab:** choose **Admin** on the login screen (token `admin:admin` by default)

Useful `.env` knobs:

```bash
SEED_CUSTOMERS=100
SEED_COUNTRY=India
ADMIN_TOKEN=admin:admin
NEXT_PUBLIC_API_BASE=http://127.0.0.1:18000
```

Rebuild the frontend image after changing `NEXT_PUBLIC_API_BASE`.

## Connection settings reference

| Variable | Purpose |
|---|---|
| `AEROSPIKE_HOSTS` | Comma-separated seeds: `host` or `host:port` (preferred) |
| `AEROSPIKE_HOST` / `AEROSPIKE_PORT` | Single-seed fallback when `AEROSPIKE_HOSTS` is empty |
| `AEROSPIKE_NAMESPACE` | Namespace (default `bank`) |
| `AEROSPIKE_USER` / `AEROSPIKE_PASSWORD` | Optional database credentials |
| `AEROSPIKE_CONFIG_FILE` | Optional extra env file for the API |

The API and Admin ingest use the same settings as the seeder.

## More detail

- Ops, native seed, and Aerospike-only bring-up: [`ops/README.md`](ops/README.md)
- Backend (local `uv` run): [`backend/README.md`](backend/README.md)
- Frontend (local `npm` run): [`frontend/README.md`](frontend/README.md)
- Approved schema: [`docs/modeling/customer-360-schema-guide.md`](docs/modeling/customer-360-schema-guide.md)
