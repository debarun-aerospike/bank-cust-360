# Customer 360 Netbanking / Mobile Banking View — Implementation Plan

**Status:** Gates 0–5 in place — Next.js UI at `frontend/`  
**Date:** 2026-09-30  

**Frontend:** `frontend/README.md` — http://127.0.0.1:4000 (API http://127.0.0.1:8000)

---

## 1. Objective

Build a **Customer 360** experience that simulates a retail bank customer logging into **netbanking or mobile banking** and viewing their **customer profile plus linked accounts with computed balances**, plus an **Admin / load lab** screen that drives configurable read/write traffic against a large seeded dataset and shows **live app-side latency and throughput charts**.

### 1.1 Business outcome

#### A. Customer 360 accounts home

Given a known **Customer ID** (session identity after login), the system returns:

1. **Customer details** from a Customer Master source (Customer No., Name, Salutation, Status, and related profile attributes).
2. **Linked accounts** across product lines:
   - Savings / Current accounts
   - Fixed / Term Deposits
   - Loans
   - Cards
3. For each account, a **computed Balance** derived from **Booking** bucket data required for balance computation.
4. For each account, a **Product Description** from Product Master.
5. A **single assembled response** suitable for a banking “accounts home” screen:
   - Customer details block
   - Account detail rows: Currency, Account Status, Product Description, Balance

#### B. Admin load & observability screen

Operators (demo / lab users) can open an **Admin** UI that:

1. Displays **inventory stats** from the live database, including at minimum:
   - Total customers (**≥ 5,000,000** in the seeded dataset)
   - Total accounts (and optionally breakdowns by Savings/Current, Fixed/Term Deposits, Loans, Cards)
   - Other agreed counters (e.g., products, booking records) if available cheaply
2. Lets the operator **set target Read TPS** and **Write TPS** (and start / stop / ramp load).
3. Shows a set of **dynamic charts** that update on the fly as load is cranked up:
   - Latency (app-side; e.g., p50 / p95 / p99 over a sliding window)
   - Achieved Read TPS
   - Achieved Write TPS
4. Reflects load changes **live** (no full page reload); charts scroll/update as targets change.

### 1.2 Proposed application stack (subject to review)

| Layer | Technology | Role |
|---|---|---|
| Frontend | React or Next.js | Netbanking / mobile-banking Customer 360 UI **and** Admin load-control dashboard with live charts |
| Backend | Python (API + load worker) | Customer 360 assembly; inventory/stats API; load generator control; app-side metrics stream |
| Data store | Aerospike cluster | Persistent / low-latency store for master, product, account, and booking data; large seed (≥5M customers) |

### 1.3 Non-goals for the first delivery (unless added after review)

- Full payments, transfers, statement history, or card management
- Real bank authentication (OTP, MFA, device binding) beyond a **simulated login** that resolves to Customer ID
- Cross-bank aggregation or open-banking connectors
- Aerospike **cluster operations** sizing, XDR, backup/restore runbooks (ops docs); the Admin screen measures **application-side** latency/throughput, not a full AMC replacement
- Mapping relational “tables” 1:1 into Aerospike sets without an access-pattern-driven model review
- Guaranteeing that configured TPS equals achieved TPS on undersized hardware — Admin must show **target vs achieved** honestly

### 1.4 Relationship to existing modeling work

This repository already contains banking profile clarification and review artifacts under `docs/modeling/`. Those cover a broader CRUD-oriented profile service. **This plan focuses on the Customer 360 / accounts-home read path plus Admin load lab** described above. After plan approval, clarification and Aerospike modeling for this use case should be completed (or reconciled with existing docs) **before** client implementation, per project `AGENTS.md`.

---

## 2. Functional logic (required assembly pipeline)

The backend must implement the following logical steps for one Customer 360 read. Physical Aerospike keys, sets, and denormalization choices are **not** decided here; they belong to the modeling phase after clarification.

```text
Customer ID (login / session input)
        │
        ▼
[1] Customer Master → Customer details (incl. Customer No., Name, Salutation, Status, …)
        │
        ▼
[2] Using Customer No. → linked accounts from Savings/Current + Fixed/Term Deposits + Loans + Cards
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
[3] Booking buckets     [4] Product Master   (per account)
    → Balance compute   → Product Description
        │                  │
        └────────┬─────────┘
                 ▼
[5] Final response: Customer Details + Account rows
    (Currency, Account Status, Product Description, Balance)
```

### 2.1 Step detail

| Step | Input | Source (logical) | Output | Notes |
|---|---|---|---|---|
| 1 | Customer ID | Customer Master | Customer details including Customer No. | Fail closed if customer missing or not eligible to view accounts |
| 2 | Customer No. | Savings/Current, Fixed/Term Deposits, Loans, Cards | Account list (all linked product lines) | Preserve product-line origin for UI grouping if required |
| 3 | Account identifiers | Booking | Buckets needed for balance; computed Balance | Balance formula must be explicit and testable |
| 4 | Product / product-type key on account | Product Master | Product Description | Handle missing product gracefully |
| 5 | Results of 1–4 | Assembler | API response DTO | Stable contract for frontend |

### 2.2 Target response shape (logical contract)

Illustrative only — field list to be finalized in clarification:

```json
{
  "customer": {
    "customerId": "...",
    "customerNo": "...",
    "salutation": "...",
    "name": "...",
    "status": "..."
  },
  "accounts": [
    {
      "accountId": "...",
      "productLine": "SAVINGS_CURRENT|TERM_DEPOSIT|LOAN|CARD",
      "currency": "...",
      "accountStatus": "...",
      "productDescription": "...",
      "balance": 0.0
    }
  ]
}
```

---

## 2A. Admin load lab — functional design

### 2A.1 Purpose

Demonstrate that Customer 360 (and related write paths) can run against a **large** Aerospike-backed dataset while operators **dial read/write intensity** and watch **app-side** latency and throughput update live.

### 2A.2 Admin UI capabilities

| Control / panel | Behavior |
|---|---|
| Inventory stats | Show live or periodically refreshed totals: customers (≥5M seeded), accounts (total + optional per product line), and other agreed counters |
| Target Read TPS | Numeric input (and optional slider); applies to load generator when running |
| Target Write TPS | Numeric input (and optional slider); applies to load generator when running |
| Start / Stop / Pause | Start load, stop load, optionally pause without clearing chart history |
| Ramp (optional) | Step target TPS up/down over time rather than a hard jump |
| Live charts | Time-series charts updating on the fly: latency, achieved read TPS, achieved write TPS |
| Target vs achieved | Display configured targets alongside measured rates so saturation is visible |
| Error / timeout rate | Show app-observed error rate during the run (recommended for honest demos) |

### 2A.3 Metrics definitions (app-side)

All charted metrics are measured **at the application / load-worker boundary**, not as a substitute for Aerospike server dashboards.

| Metric | Definition (logical) |
|---|---|
| Achieved Read TPS | Successful Customer 360 (or agreed read mix) operations completed per second in the sliding window |
| Achieved Write TPS | Successful write operations completed per second (exact write mix finalized in clarification — e.g., contact update, booking bucket touch, account link stub) |
| Latency | End-to-end duration of each operation as observed by the worker/API client before response return; chart p50 / p95 / p99 (confirm which percentiles at Gate 0) |
| Inventory counts | Customer/account/product totals used for the Admin header; must remain readable under load without starving the load path |

### 2A.4 Architecture sketch (logical — no implementation yet)

```text
Admin UI ──► Load Control API (set target read/write TPS, start/stop)
                │
                ▼
         Load Worker(s) ──► Customer 360 reads / agreed writes ──► Aerospike
                │
                ▼
         Metrics aggregator (in-process ring buffers / time buckets)
                │
                ▼
Admin UI ◄── Metrics stream (WebSocket or SSE) + Inventory Stats API
```

Principles:

- Frontend **controls** load and **subscribes** to metrics; it does not generate high TPS from the browser.
- Backend (or a dedicated worker process co-located with the API) owns rate limiting, worker pools, and metric aggregation.
- Chart updates should be frequent enough to feel live (e.g., 1s buckets streamed every 500ms–1s) without flooding the browser.
- Inventory stats for ≥5M customers must use an **efficient** count strategy agreed in modeling (maintained counters, approximate stats, or bounded sampling — **not** a full scan on every Admin poll unless explicitly accepted as a demo-only exception).

### 2A.5 Illustrative Admin API contract (logical)

| Endpoint (illustrative) | Purpose |
|---|---|
| `GET /api/v1/admin/inventory` | Customer/account/(optional) product totals |
| `GET /api/v1/admin/load` | Current run state, target TPS, achieved TPS snapshot |
| `PUT /api/v1/admin/load` | Set target read/write TPS; start/stop/pause |
| `GET /api/v1/admin/metrics/stream` | SSE/WebSocket stream of latency + TPS time buckets |

Exact paths and auth for Admin (demo token vs open lab mode) are Gate 1 decisions.

---

## 3. Open requirements (must resolve before schema and code)

These are intentionally recorded as gaps. Do **not** invent answers during implementation without an approved assumption and reconsideration trigger.

### 3.1 Identity and eligibility

1. Customer ID vs Customer No.: formats, uniqueness, immutability, and which is the login key.
2. Whether inactive / closed / blocked customers still receive an accounts list (empty vs error vs redacted).
3. Joint / multi-owner accounts: included or not; how ownership is represented.

### 3.2 Account universe

4. Exact account fields available on Savings/Current, Fixed/Term Deposits, Loans, and Cards (currency, status, product key, etc.).
5. Whether closed / dormant / pledged accounts appear on the home screen.
6. Ordering of accounts (product line, nickname, open date, balance, bank-defined display order).
7. Expected and p99 account counts per customer (skew bound for latency and pagination).

### 3.3 Balance computation

8. Exact booking **bucket codes** required per product line.
9. Balance formula (e.g., available vs ledger; signs for loans; FX for multi-currency).
10. Precision, rounding, and display scale.
11. Freshness SLA: max acceptable age of booking data for the home screen.
12. Behavior when buckets are missing, partial, or inconsistent.

### 3.4 Product master

13. Product key used to join Product Master (code, type+subtype, etc.).
14. Locale / language of Product Description.
15. Behavior when product is retired or missing.

### 3.5 Non-functional

16. Latency target for end-to-end Customer 360 (p95 / p99) under baseline and under Admin-driven load.
17. Consistency expectation across customer, accounts, booking, and product reads (same-second snapshot vs best-effort).
18. Auth simulation: how Customer ID is established (hardcoded demo user, mock JWT, etc.).
19. Environment: local Docker Aerospike vs shared cluster; CE vs EE features if any are required.
20. Seed data volume for demo vs performance test — **customers must be ≥ 5,000,000**; confirm average accounts per customer and total account target.
21. Max Read TPS / Write TPS the Admin UI may request; worker concurrency caps; safety kill-switch.
22. Exact **write mix** under Write TPS (which mutations; idempotency; whether writes must remain realistic banking updates).
23. Metrics transport: WebSocket vs SSE vs short polling; chart window length; percentile set (p50/p95/p99).
24. How inventory totals are maintained or queried at ≥5M scale without scanning on every Admin refresh.
25. Whether Admin is open in the demo or gated behind a simple admin credential.

---

## 4. Phased implementation plan

Work proceeds in gates. **Gate N must be reviewed before Gate N+1 starts.** No application code until Gates 0–2 (or explicit waiver) are approved.

### Gate 0 — Plan approval (this document)

**Deliverable:** Reviewed and accepted version of this plan (possibly amended).  
**Status:** **Approved** — stakeholder accepted the plan (“Plan looks good”), 2026-09-29.  
**Exit criteria:**

- Objective and response contract agreed at logical level (Customer 360 **and** Admin load lab) — met
- Stack choice confirmed (React vs Next.js; Python framework preference) — still open in Gate 1 clarification Q32–Q33
- Admin chart metrics and load-control UX accepted (§2A) — met at plan level
- Test strategy accepted (including load-lab tests) — met at plan level
- Clarification questions in §3 prioritized for workshop — see Gate 1 clarification priority list

### Gate 1 — Clarification & access-pattern matrix

**Deliverable:** Written clarification document and access-pattern matrix for **this** Customer 360 read path (new file under `docs/modeling/` or extension of existing banking clarifications).  
**Status:** **Closed** — stakeholder answers recorded 2026-09-29; approved assumptions A-* documented in clarification file.  
**Activities:**

1. Confirm every §3 item or record approved assumptions with reconsideration triggers.
2. Document domain entities and relationships: Customer, Customer No., Savings/Current, Fixed/Term Deposit, Loan, Card accounts, Booking buckets, Product.
3. Build access-pattern matrix entries at minimum:
   - AP-C360-1: Get customer details by Customer ID
   - AP-C360-2: List linked accounts by Customer No. across product lines
   - AP-C360-3: Get booking buckets for balance by account
   - AP-C360-4: Get product description by product key
   - AP-C360-5: Assemble Customer 360 response (orchestration; may be application-only)
   - AP-ADMIN-1: Read inventory totals (customers, accounts, …)
   - AP-ADMIN-2: Configure and run read load at target TPS (Customer 360 or agreed read mix)
   - AP-ADMIN-3: Configure and run write load at target TPS (agreed write mix)
   - AP-ADMIN-4: Stream or poll app-side latency and achieved TPS metrics
4. Capture frequency, concurrency, latency, payload size, cardinality, consistency, TTL/retention for each path.
5. Partition into entity groups for sequential Aerospike design (suggested groups below — routing only, no set/index preselection):
   - **EG-1:** Customer master identity and profile attributes
   - **EG-2:** Customer ↔ accounts linkage (deposits / loans / trade)
   - **EG-3:** Booking buckets and balance inputs
   - **EG-4:** Product master reference data
   - **EG-5 (optional routing):** Inventory counters / stats records if totals are not derived from set metadata alone

**Exit criteria:** Clarification gate closed or assumptions approved; matrix complete enough to design EG-1.

### Gate 2 — Aerospike data model (one entity group at a time)

**Deliverable:** Schema guide sections per entity group; schema summary regenerated only from the guide.  
**Activities (per entity group):**

1. Resolve group-specific gaps.
2. Define record boundaries driven by access patterns (not 1:1 table mapping).
3. Define namespace/set boundaries, primary-key strategy, bins/CDTs, TTL, consistency, overflow, hot-key risks.
4. Map each access path to primary-key / bounded batch / CDT / expression / justified secondary index / exceptional scan.
5. Developer walkthrough: create+read seed path, multi-record assembly path, cleanup/cascade if any.
6. Stakeholder checkpoint before next group.
7. Cross-group validation and failure-mode checklist when all groups are reviewed.

**Important modeling constraints for this use case:**

- Do **not** turn Customer Master / Savings-Current / Term-Deposit / Loans / Cards / Booking / Product Master into Aerospike sets solely because those relational sources exist.
- Prefer primary-key and bounded batch reads for the login home path; avoid secondary-index-heavy routine access.
- Balance computation may be application-side from fetched buckets, or server-side expressions if justified and version-verified — decide after formula and bucket layout are known.
- Deliberate denormalization is allowed when it removes fan-out that exists only to assemble the home-screen response; document maintenance cost.

**Exit criteria:** Schema guide complete for Customer 360; mandatory review checks pass or exceptions accepted; summary in sync.

### Gate 3 — Local Aerospike and seed data

**Deliverable:** Local cluster bring-up notes (Docker), **large** seed dataset (≥5M customers), load/verify script outline, inventory verification.  
**Activities:**

1. Run Aerospike CE locally (ports 3000–3002; default namespace `test` unless modeling specifies otherwise).
2. Bulk-load seed customers (**≥ 5,000,000**), linked accounts across product lines, booking buckets, and products matching the approved schema.
3. Provide a **fast path** for CI/dev: a small fixture set for unit/integration tests, plus a documented large-seed job for the Admin demo (may run overnight or on a dedicated machine).
4. Verify primary-key / batch reads for AP-C360-1..4 independently of the API.
5. Verify inventory totals exposed to Admin match seeded counts (AP-ADMIN-1).
6. Document seed Customer IDs for the UI demo and the ID range used by the load worker’s random/sequential key picker.

**Exit criteria:** Seeded cluster meeting the ≥5M customer floor (or approved staging environment with that scale); inventory API returns expected totals; manual Customer 360 read of seed records succeeds.

### Gate 4 — Python backend (Customer 360 API + Admin load lab)

**Deliverable:** Python service implementing the assembly pipeline, inventory/stats, load control, and metrics streaming behind a versioned HTTP API.  
**Suggested structure (illustrative):**

- `app/api` — HTTP routes (`GET /api/v1/customers/{customer_id}/360`, Admin routes from §2A.5)
- `app/services/customer360` — orchestration of steps 1–5
- `app/services/balance` — pure balance computation from buckets (unit-testable)
- `app/services/loadgen` — rate-limited read/write workers; target vs achieved TPS
- `app/services/metrics` — sliding-window latency histograms and TPS buckets; stream publisher
- `app/services/inventory` — customer/account/(optional) product totals for Admin
- `app/repositories` — Aerospike access adapters (singleton client, reused policies)
- `app/schemas` — request/response DTOs and validation
- `app/auth` — simulated session → Customer ID; Admin gate if required

**Activities:**

1. Choose Python web framework (FastAPI recommended for OpenAPI + typing + SSE/WebSocket options; confirm at Gate 0).
2. Implement Aerospike client lifecycle (one client per process; connection pool/warmup sized for peak Admin TPS).
3. Implement repositories for AP-C360-1..4 and inventory (AP-ADMIN-1).
4. Implement balance pure functions with explicit formula from Gate 1.
5. Implement assembler with partial-failure policy (agreed in clarification).
6. Implement load generator: set target Read TPS / Write TPS; start/stop/pause; worker pool; random/sequential Customer ID selection from seeded range.
7. Instrument every load operation with app-side latency; publish achieved Read/Write TPS and latency percentiles on a live stream.
8. Expose health and readiness endpoints (process up; Aerospike reachable; optionally “load running” state).
9. Structured logging and correlation IDs for the assembly path; separate load-run IDs for Admin sessions.
10. OpenAPI / typed responses matching frontend contracts (Customer 360 + Admin).

**Exit criteria:** API returns correct Customer 360 for seed customers; Admin can set TPS and observe live metrics; inventory shows ≥5M customers after large seed; backend tests green (Gate 6).

### Gate 5 — Frontend (React or Next.js) — Customer 360 + Admin

**Deliverable:** Sleek accounts-home UI **and** Admin load lab with live charts.  
**Activities:**

1. Confirm React SPA vs Next.js (SSR not required for demo; Next.js App Router acceptable if preferred).
2. Navigation between **Customer 360** (end-user simulation) and **Admin** (load lab).
3. Simulated login screen → selects or submits Customer ID / demo username.
4. Accounts overview:
   - Customer header (salutation, name, status)
   - Account list/table or mobile-style cards: Currency, Status, Product Description, Balance
   - Optional grouping by product line (Savings/Current, Fixed/Term Deposits, Loans, Cards)
5. **Admin screen:**
   - Inventory panel: total customers (≥5M after large seed), total accounts, optional product-line breakdowns
   - Controls: target Read TPS, target Write TPS, Start / Stop / Pause (and optional Ramp)
   - Dynamic charts updating on the fly as load changes:
     - Latency (p50 / p95 / p99 as agreed)
     - Achieved Read TPS (with target overlay)
     - Achieved Write TPS (with target overlay)
   - Optional error-rate sparkline / counter during the run
6. Metrics subscription (SSE or WebSocket) with graceful reconnect; charts must update without full reload when TPS is cranked up or down.
7. Loading, empty, error, and unauthorized states for both screens.
8. Responsive layout for desktop netbanking and mobile banking widths; Admin optimized for desktop demo.
9. No cards-for-decoration; keep interaction containers purposeful; brand the banking demo clearly.

**Exit criteria:** End-to-end demo: Customer 360 against API + Aerospike; Admin dials TPS and charts move live; UI tests covering critical paths (Gate 6).

### Gate 6 — Test hardening and demo readiness

**Deliverable:** Automated unit + integration suites; short demo script; known limitations list.  
**Exit criteria:** CI (or local makefile) runs unit and integration tests; demo Customer IDs documented; open risks listed.

---

## 5. Detailed implementation steps (ordered checklist)

Use this as the execution backlog after Gate 0 approval.

### A. Requirements and modeling

1. Workshop §3 open questions; write clarification document (Customer 360 + Admin load lab).
2. Finalize Customer 360 response DTO and error model.
3. Finalize Admin inventory/metrics/load-control contracts (§2A).
4. Finalize balance formula and bucket inventory per product line.
5. Produce access-pattern matrix AP-C360-1..5 and AP-ADMIN-1..4.
6. Entity-group plan EG-1..EG-5 with review status.
7. Design and review EG-1 (Customer).
8. Design and review EG-2 (Accounts linkage).
9. Design and review EG-3 (Booking / balance inputs).
10. Design and review EG-4 (Product master).
11. Design and review EG-5 if inventory counters are required for Admin totals at ≥5M scale.
12. Cross-group validation + failure-mode checklist.
13. Publish schema guide + derived schema summary.

### B. Platform

14. Docker Compose (or equivalent) for Aerospike local cluster.
15. Backend project skeleton + **uv** project (`pyproject.toml` / `uv.lock`); always use `uv sync` / `uv run` (never pip/venv directly).
16. Frontend project skeleton + design tokens / brand direction.
17. Shared env config: Aerospike hosts, namespace, API base URL, demo users, loadgen limits.

### C. Data

18. Seed writer matching schema contracts (small fixture set for CI).
19. Large bulk seeder: **≥ 5,000,000 customers** plus linked accounts/booking/products; progress reporting.
20. Seed scenarios: single account; multi-line mix; zero accounts; missing product; missing buckets; blocked customer; large account fan-out (bounded).
21. Inventory counter strategy (maintained counters vs metadata) verified against seed.
22. Manual verification of key reads and inventory totals.

### D. Backend

23. Aerospike client module (singleton; pools sized for load lab).
24. Repository methods for AP-C360-1..4.
25. Balance calculator module.
26. Customer360 service assembler.
27. HTTP endpoint + validation + error mapping.
28. Simulated auth middleware.
29. Inventory service + Admin inventory API.
30. Load generator (target Read/Write TPS, start/stop/pause, worker pool, key picker).
31. Metrics aggregator + live stream (latency percentiles, achieved Read/Write TPS).
32. Admin load control API.
33. Observability (logs, load-run IDs, basic process metrics).

### E. Frontend

34. Login / customer select screen.
35. Customer 360 view binding to API.
36. Formatting: currency, balance, status badges.
37. **Admin screen:** inventory stats, TPS controls, Start/Stop/Pause.
38. **Live charts:** latency, read TPS, write TPS (target overlays); update on the fly as load changes.
39. Metrics stream client with reconnect.
40. Empty / error / loading UX for both apps.
41. Responsive polish and motion for hierarchy (subtle, intentional).

### F. Quality

42. Implement unit tests (§6).
43. Implement integration tests (§7), including Admin/load-lab cases.
44. Optional contract tests (OpenAPI consumer checks).
45. Demo rehearsal: crank Read/Write TPS and show charts tracking live (only after Gates complete).
46. README for reviewers (only if requested after plan approval).

---

## 6. Unit test plan

Unit tests must not require a live Aerospike cluster. Prefer pure functions and mocked repository boundaries.

### 6.1 Balance computation (`services/balance`)

| ID | Scenario | Expected |
|---|---|---|
| U-BAL-01 | All required buckets present for a deposit | Balance equals documented formula |
| U-BAL-02 | Loan buckets with debit/credit sign rules | Signed balance matches formula |
| U-BAL-03 | Card account bucket set | Balance matches formula |
| U-BAL-03b | Fixed/Term Deposit bucket set | Balance matches formula |
| U-BAL-03c | Savings/Current bucket set | Balance matches formula |
| U-BAL-04 | Missing required bucket | Agreed behavior (error vs null vs zero) |
| U-BAL-05 | Extra unexpected buckets ignored | Result unchanged |
| U-BAL-06 | Zero amounts | Balance 0 with correct currency scale |
| U-BAL-07 | Rounding / decimal precision edge cases | Matches bank rounding rule |
| U-BAL-08 | Negative available / overdraft case (if in scope) | Matches formula |
| U-BAL-09 | Multi-currency input rejected or handled | Per clarification |
| U-BAL-10 | Property-style checks on synthetic bucket maps | Invariants hold |

### 6.2 Response assembler (`services/customer360`)

| ID | Scenario | Expected |
|---|---|---|
| U-ASM-01 | Customer + N accounts + products + balances | Full DTO shape |
| U-ASM-02 | Customer with zero accounts | Customer block + empty accounts array |
| U-ASM-03 | Account missing product description | Fallback string or null per contract |
| U-ASM-04 | Account missing booking data | Per partial-failure policy |
| U-ASM-05 | Mixed product lines ordering | Stable order rule applied |
| U-ASM-06 | Duplicate account IDs across sources (if possible) | Dedup or error per policy |
| U-ASM-07 | Customer not found from repo | Maps to not-found error type |
| U-ASM-08 | Customer status not viewable | Maps to forbidden / empty policy |
| U-ASM-09 | Repository timeout/error injection | Propagates typed error; no partial corrupt DTO unless allowed |
| U-ASM-10 | Field mapping: salutation/name/status/currency/status/description/balance | Exact field names and types |

### 6.3 Repository adapters (mocked Aerospike client)

| ID | Scenario | Expected |
|---|---|---|
| U-REPO-01 | Customer get by ID builds correct key tuple | Key contract asserted |
| U-REPO-02 | Accounts fetch by Customer No. | Calls expected sets/keys or batch; returns mapped domain objects |
| U-REPO-03 | Booking fetch by account | Maps bins/CDTs to bucket structure |
| U-REPO-04 | Product fetch by product key | Maps description field |
| U-REPO-05 | Record not found → domain None/NotFound | No raw SDK leak to service layer |
| U-REPO-06 | Partial batch results | Per-key failures handled |
| U-REPO-07 | Bin/type coercion errors | Clear domain error |

### 6.4 API layer (framework test client, repos mocked)

| ID | Scenario | Expected |
|---|---|---|
| U-API-01 | `GET` Customer 360 happy path | 200 + schema-valid body |
| U-API-02 | Unknown customer | 404 (or agreed code) |
| U-API-03 | Unauthenticated / bad session | 401 |
| U-API-04 | Forbidden customer status | 403 or agreed empty payload |
| U-API-05 | Upstream Aerospike failure | 503 or 500 per policy; no stack trace leak |
| U-API-06 | Invalid Customer ID format | 422/400 |
| U-API-07 | Response Content-Type and OpenAPI schema | Compliant |
| U-API-08 | Correlation ID header echoed/logged | Present |

### 6.5 Auth simulation

| ID | Scenario | Expected |
|---|---|---|
| U-AUTH-01 | Valid demo token/session → Customer ID | Injected correctly |
| U-AUTH-02 | Expired / malformed session | 401 |
| U-AUTH-03 | Session Customer ID mismatch with path ID (if both used) | 403 |

### 6.6 Frontend unit tests (component / hook level)

| ID | Scenario | Expected |
|---|---|---|
| U-FE-01 | Customer header renders salutation + name + status | Visible correct text |
| U-FE-02 | Account row renders currency, status, description, balance | Formatted correctly |
| U-FE-03 | Loading skeleton/spinner while fetching | Shown |
| U-FE-04 | Empty accounts state | Friendly empty message |
| U-FE-05 | API error state | Error message + retry affordance |
| U-FE-06 | Balance formatter (locale/currency) | Snapshot or value assertions |
| U-FE-07 | Product-line grouping (if enabled) | Sections correct |
| U-FE-08 | Admin inventory panel shows customer/account totals | Values from mocked API rendered |
| U-FE-09 | Admin Read TPS / Write TPS inputs update local target state | Controlled inputs work |
| U-FE-10 | Start/Stop toggles load control API calls | Correct payloads |
| U-FE-11 | Chart components render series from metric buckets | Latency / read TPS / write TPS series visible |
| U-FE-12 | Incoming metric events append/update charts without remount | Live update behavior |
| U-FE-13 | Target overlays drawn on TPS charts | Target lines/markers present |

### 6.7 Load generator & metrics (backend unit)

| ID | Scenario | Expected |
|---|---|---|
| U-LOAD-01 | Target Read TPS=0 → no read ops issued | Idle |
| U-LOAD-02 | Target Read TPS=N with mocked clock | Issued ops ≈ N/sec within tolerance |
| U-LOAD-03 | Target Write TPS=N with mocked clock | Issued ops ≈ N/sec within tolerance |
| U-LOAD-04 | Stop cancels in-flight scheduling promptly | No further ops after stop window |
| U-LOAD-05 | Pause freezes scheduling; resume continues | State machine correct |
| U-LOAD-06 | Latency histogram records durations | p50/p95/p99 computable |
| U-LOAD-07 | Achieved TPS bucket math over 1s windows | Matches counted completions |
| U-LOAD-08 | Concurrent set-target while running | New targets applied without crash |
| U-LOAD-09 | Worker errors counted in error rate | Surfaced in metrics snapshot |
| U-LOAD-10 | Key picker stays within seeded ID range | No out-of-range IDs |

### 6.8 Admin API (framework test client, loadgen mocked)

| ID | Scenario | Expected |
|---|---|---|
| U-ADM-01 | `GET` inventory returns customer/account totals | Schema-valid |
| U-ADM-02 | `PUT` load with read/write TPS starts run | 200; state=running |
| U-ADM-03 | `PUT` stop ends run | state=stopped |
| U-ADM-04 | Invalid negative TPS | 422/400 |
| U-ADM-05 | Metrics stream emits buckets | Event shape valid |
| U-ADM-06 | Unauthorized Admin access (if gated) | 401/403 |

---

## 7. Integration test plan

Integration tests use a **real Aerospike** (Docker) and a **running API** (or in-process app with live client). Frontend E2E optional but recommended for demo confidence.

### 7.1 Environment

- Aerospike CE via Docker, ports 3000–3002
- Namespace/sets/keys per approved schema guide
- Deterministic seed loaded before each suite (or transactional fixtures per test class)
- Python test runner (pytest); frontend E2E via Playwright or Cypress if Gate 0 selects it

### 7.2 Data fixtures (minimum)

| Fixture | Purpose |
|---|---|
| F-HAPPY | Active customer, ≥1 deposit, ≥1 loan, ≥1 trade; complete buckets; valid products |
| F-EMPTY | Active customer, no accounts |
| F-BLOCKED | Customer status not allowed to view accounts |
| F-MISS-PROD | Account with unknown product key |
| F-MISS-BOOK | Account with missing/partial booking buckets |
| F-SKEW | Customer at agreed high account count (bounded for CI) |
| F-SINGLE-LINE | Only deposits (or only loans) |
| F-SCALE-META | Documented large-seed job producing **≥5M customers** (may be env-gated in CI) |
| F-INV | Known inventory counts for small seed so Admin inventory assertions are exact in CI |

### 7.3 Backend integration tests

| ID | Scenario | Expected |
|---|---|---|
| I-BE-01 | Seed F-HAPPY → `GET` Customer 360 | Customer fields match seed; account count and lines match; balances match independently computed oracle |
| I-BE-02 | F-EMPTY | 200 with empty accounts |
| I-BE-03 | Unknown Customer ID | 404 |
| I-BE-04 | F-BLOCKED | Agreed status code / body |
| I-BE-05 | F-MISS-PROD | Product description fallback; other accounts unaffected |
| I-BE-06 | F-MISS-BOOK | Balance field follows partial-failure policy |
| I-BE-07 | Step isolation: customer record readable by key | Direct repository read succeeds |
| I-BE-08 | Accounts linkage returns union of product lines | No silent drop of a line |
| I-BE-09 | Booking buckets readable for each happy account | Bucket map non-empty as seeded |
| I-BE-10 | Product master readable for each happy product key | Description equals seed |
| I-BE-11 | Balance oracle: recompute in test from raw buckets | Equals API balance within rounding tolerance |
| I-BE-12 | Concurrent identical `GET`s | Stable results; no client pool exhaustion |
| I-BE-13 | Aerospike down mid-request | Graceful 5xx; client recovers after restart (optional soak) |
| I-BE-14 | Health/readiness reflects Aerospike availability | readiness fails when cluster unreachable |
| I-BE-15 | F-SKEW latency smoke | Completes under agreed CI budget (document if soft) |
| I-BE-16 | `GET` inventory on F-INV | Totals match seeded counts |
| I-BE-17 | Start read load at modest TPS against live cluster | Achieved Read TPS within tolerance; metrics stream emits latency buckets |
| I-BE-18 | Start write load at modest TPS | Achieved Write TPS within tolerance; writes visible per agreed mix |
| I-BE-19 | Increase target Read TPS mid-run | Charts/metrics show higher achieved rate (or saturation gap) without restart |
| I-BE-20 | Stop load | Achieved TPS returns to ~0; no orphaned workers |
| I-BE-21 | Large-seed gate (optional/nightly): inventory customers ≥ 5,000,000 | Pass on scale environment |

### 7.4 Contract / schema integration

| ID | Scenario | Expected |
|---|---|---|
| I-CT-01 | Response validates against published OpenAPI / JSON Schema | Pass |
| I-CT-02 | Required account row fields always present when account listed | Pass |
| I-CT-03 | Enumerations (productLine, status) only allow agreed values | Pass |
| I-CT-04 | Admin inventory + load + metrics event schemas valid | Pass |

### 7.5 End-to-end / UI integration

| ID | Scenario | Expected |
|---|---|---|
| I-E2E-01 | Login as demo user → accounts home | Customer name visible; account rows match API |
| I-E2E-02 | Demo user with empty accounts | Empty state shown |
| I-E2E-03 | API forced 500 | Error UI shown |
| I-E2E-04 | Mobile viewport | Layout usable; balances readable |
| I-E2E-05 | Desktop viewport | Netbanking-style overview usable |
| I-E2E-06 | Open Admin → inventory shows customer/account totals | Values visible and non-zero for seeded env |
| I-E2E-07 | Set Read TPS and Start → latency + read TPS charts update live | Series points increase over time |
| I-E2E-08 | Set Write TPS and Start → write TPS chart updates live | Series points increase over time |
| I-E2E-09 | Crank Read TPS upward while running | Charts reflect higher target/achieved without page reload |
| I-E2E-10 | Stop → TPS charts fall toward zero | Controls and charts consistent |

### 7.6 Negative and security-light checks (demo-grade)

| ID | Scenario | Expected |
|---|---|---|
| I-SEC-01 | Access another customer’s ID without session entitlement | Denied |
| I-SEC-02 | Injection-like Customer ID strings | Rejected safely |
| I-SEC-03 | No Aerospike credentials or secrets in API responses | Pass |
| I-SEC-04 | Unauthenticated Admin load control (if Admin is gated) | Denied |
| I-SEC-05 | Absurd TPS above configured max | Rejected or clamped with clear feedback |

---

## 8. Test data oracle for balances

To avoid circular “API agrees with itself” tests:

1. Store **raw booking buckets** in fixtures.
2. Implement the **same documented formula** in a test-only oracle module (or share the pure `balance` module — preferred — and independently assert against hand-calculated expected values in tables).
3. For I-BE-01 / I-BE-11, compare API `balance` to:
   - Hand-calculated expected constants in the fixture file, **and**
   - Pure function output from raw buckets.

Any formula change requires updating the clarification doc, unit tables, and fixtures together.

---

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Relational table-to-set copy without access-pattern design | Hot keys, unbounded CDTs, slow home page | Enforce Gates 1–2; reject 1:1 mapping without justification |
| Unspecified balance formula | Incorrect money display | Block Gate 4 until formula + buckets approved |
| N+1 Aerospike reads in assembler | p99 latency miss | Prefer bounded batch; measure in I-BE-15 / load lab |
| Partial failure ambiguity | Wrong UX / compliance issues | Explicit policy in clarification; cover U-ASM-04 / I-BE-06 |
| TTL mismatch (profile vs accounts vs booking) | Empty homepage or stale balances | Model TTLs per entity group; test expired-record behavior if TTL used |
| Scope creep into full banking platform | Delayed demo | Hold non-goals in §1.3 |
| ≥5M seed time/disk on laptop | Demo blocked or CI flaky | Separate small CI seed vs large demo seed; nightly/scale job for I-BE-21 |
| Full-set scan for inventory under load | Admin poll amplifies load, skews charts | Prefer maintained counters or cheap metadata; forbid scan-on-poll unless waived |
| Browser-side load generation | Unrealistic TPS, UI jank | Backend load worker only; UI only controls + charts |
| Target TPS ≫ hardware capacity | Charts look “broken” | Show target vs achieved; document max safe TPS; clamp or warn |
| Metrics stream flooding the browser | UI freeze | Fixed-size ring buffer; 1s buckets; downsample |
| Write mix unclear | Unsafe or meaningless Write TPS | Gate 1 must define write operations before Gate 4 loadgen |

---

## 10. Suggested repository layout (after approval only)

```text
planning/                          # this plan
docs/modeling/                     # clarification, access matrix, schema guide, summary
backend/                           # Python API + loadgen + metrics
frontend/                          # React or Next.js (Customer 360 + Admin)
ops/docker/                        # Aerospike local compose (if needed)
ops/seed/                          # small fixtures + large ≥5M bulk seeder
tests/                             # shared integration harness (optional)
```

Exact package names to be chosen at Gate 4/5; do not create these trees until the plan is approved.

---

## 11. Review checklist for this plan

Please confirm or amend:

1. Objective and five-step assembly logic are correct for the intended demo.
2. Admin load lab (§2A) is in scope: target Read/Write TPS, inventory (≥5M customers), live latency/TPS charts.
3. React vs Next.js preference.
4. Python framework preference (e.g., FastAPI).
5. Whether login is purely simulated with selectable demo Customer IDs.
6. Priority order of §3 clarification questions for the first workshop (especially write mix, inventory counting, max TPS).
7. Whether existing `docs/modeling/banking-customer-profile-*` should be superseded, extended, or kept separate from this Customer 360 read path.
8. Acceptance of Gates 0→6 and “no code until Gates 0–2” (or a documented waiver).
9. Any additional account fields required on each row beyond Currency, Account Status, Product Description, Balance.
10. Balance: available vs ledger vs both on the home screen.
11. Latency percentiles to chart (p50/p95/p99 or subset) and metrics transport (SSE vs WebSocket).
12. Whether large ≥5M seed is required on every developer machine or only on a shared/demo environment.
13. Test depth required for first demo (unit + backend integration only vs full Playwright E2E including Admin charts).

---

## 12. Next action after approval

1. ~~Gates 0–5 (model, ops, FastAPI, Next.js UI).~~ **Done**
2. **Next (optional):** Gate 6 — broader automated/E2E tests and demo script.
