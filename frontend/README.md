# Gate 5 — Next.js Customer 360 + Admin UI

Aerospike brand colors from `planning/UI-styles.md`: `#F8F413`, `#0D1B32`, `#F2F1ED`.

For the full stack in Docker (Aerospike + seed + API + UI), from the repo root:

```bash
docker compose up --build -d
```

Open http://127.0.0.1:4000 — see `ops/README.md`.

## Setup

```bash
cd frontend
npm install
```

## Run

Backend must be on `http://127.0.0.1:8000` (see `backend/README.md`).

```bash
npm run dev
```

Open http://127.0.0.1:4000

- **/login** — mock Customer ID (e.g. `0000001`)
- **/c360** — accounts home with product-line tabs
- **/admin** — inventory, load TPS, ingest, live WebSocket charts

Env: `.env.local` (`NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_ADMIN_TOKEN`).
