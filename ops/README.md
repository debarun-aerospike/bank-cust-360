# Ops — Local Aerospike + full-stack Docker Compose

Bring-up for the approved Customer 360 schema (`docs/modeling/customer-360-schema-guide.md`) and the Gate 4–5 API/UI lab.

## Prerequisites

- Docker / Docker Compose
- Enough RAM for `data-size` in `docker/aerospike.conf` (default **4G** for laptop seeds)

Optional (native/dev outside Docker): [uv](https://docs.astral.sh/uv/), Node.js 22+

Enterprise image `aerospike/aerospike-server-enterprise` includes a built-in evaluation feature key for single-node lab use (Database 6.1.0+).

## Full stack (recommended)

From the **repository root**:

```bash
cp .env.example .env   # optional
docker compose up --build -d
docker compose ps
```

| Service   | URL / address                          |
|-----------|----------------------------------------|
| UI        | http://127.0.0.1:4000                  |
| API docs  | http://127.0.0.1:18000/docs            |
| Aerospike | `127.0.0.1:13000` (namespace **`bank`**) |

Demo login Customer ID after default seed: `0000001` (Bearer `mock:0000001`).  
Admin token: `admin:admin` (override with `ADMIN_TOKEN`).

### External Aerospike instead of the Compose DB

1. In `.env`, set seeds / optional auth:

```bash
AEROSPIKE_HOSTS=10.0.0.11:3000,10.0.0.12:3000
AEROSPIKE_NAMESPACE=bank
AEROSPIKE_USER=          # optional
AEROSPIKE_PASSWORD=      # optional
# AEROSPIKE_CONFIG_FILE=./ops/aerospike.client.env
```

2. Start app only:

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml up --build -d
```

3. Seed:

```bash
docker compose -f docker-compose.yml -f docker-compose.external.yml run --rm --no-deps seed \
  --hosts="$AEROSPIKE_HOSTS" --customers=100 --country=India
```

See root `README.md` and `ops/aerospike.client.env.example`.

Seed size / country via `.env`:

```bash
SEED_CUSTOMERS=100
SEED_COUNTRY=India
```

Namespace storage (bundled lab) is in-memory — recreating the Aerospike container loses data. Reseed with:

```bash
docker compose run --rm seed
```

Stop / remove:

```bash
docker compose down
```

## Aerospike only

```bash
cd ops/docker
docker compose up -d
docker compose ps
```

Client: `127.0.0.1:13000` (mapped to container 3000). Namespace: **`bank`** (not `test`).

## Seed (native uv)

When Aerospike is already up (Compose full stack or Aerospike-only):

```bash
cd ops/seed
uv sync

# Against host-mapped port
uv run python seed.py --customers 100 --port 13000 --country India

# Shared demo (≥5M) — raise aerospike.conf data-size first
uv run python seed.py --customers 5000000 --checkpoint-every 10000 --port 13000 --country India
```

`--customers` is the Admin ingestion count knob (AP-ADMIN-5).

Demo Customer IDs after a run of N: `0000001` … zero-padded 7-digit N.

## Verify

```bash
cd ops/seed
uv run python verify_c360.py --customer 0000001 --port 13000
```

Checks `inventory/totals` and assembles a Customer 360-style account list (Active only, embedded `productDesc`, booking balance).

## Notes

- Sets are created on first write (`customers`, `cust_accts`, `accounts`, `booking`, `products`, `inventory`).
- Inventory is checkpointed during seed (not per-record) to avoid hot keys.
- For ≥5M customers, use a shared host and increase `storage-engine memory { data-size ... }` in `aerospike.conf`.
- Seed/backend Python deps live in their `pyproject.toml` / `uv.lock` files.
- Browser calls the API at `NEXT_PUBLIC_API_BASE` (default `http://127.0.0.1:18000`); rebuild the frontend image after changing it.
- Host API port is **18000** (container listens on 8000) so it does not clash with common local tools on 8000.
