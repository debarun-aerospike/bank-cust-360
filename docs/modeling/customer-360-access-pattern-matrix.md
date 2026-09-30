# Customer 360 + Admin Load Lab: Access-Pattern Matrix

## Status

- Phase: Gate 1 **closed**; matrix updated from confirmed clarifications + approved assumptions
- Companion: `docs/modeling/customer-360-clarifications.md`
- Mechanism columns filled only where Gate 2 has designed the path (EG-1+)

## Customer 360 paths

### AP-C360-1 — Get customer details by Customer ID

| Attribute | Value |
|---|---|
| Lookup input | 7-digit Customer ID (= Customer No.) |
| Key known? | Yes |
| Data read | salutation, name, status (+ id/no from key) |
| Frequency | Interactive + Admin Read TPS (max 5000) |
| Latency | Demo-grade (lab/Docker) |
| Cardinality | 0..1 |
| Consistency | Best-effort |
| Retention | Persistent |
| Ineligible | Unknown id → not found; status only Active/Dormant in seed |
| Mechanism | **EG-1:** primary-key get on customer record |

### AP-C360-2 — List linked accounts by Customer No.

| Attribute | Value |
|---|---|
| Lookup input | Customer No. (= Customer ID) |
| Key known? | Yes |
| Data read | Accounts for customer across Savings/Current, Fixed/Term Deposits, Loans, Cards; incl. embedded `productDesc` |
| Fan-out | Avg 2, p99 2, max 5 |
| Filters | Default `Active` accounts; dropdown may include Dormant/Closed/Pledged/Hidden; omit if `productDesc` empty |
| Ordering | PRIMARY then JOINT; UI groups by product line (four tabs/sections) |
| Retention | Persistent |
| Mechanism | **EG-2:** PK get `cust_accts` → batch get ≤5 `accounts` (no SI) |

### AP-C360-3 — Get booking buckets for balance by account

| Attribute | Value |
|---|---|
| Lookup input | Account ID |
| Buckets | Savings/Current & Fixed/Term: ledger, hold, float; Loan & Card: principal, interest (A-BUCKETS) |
| Formula | A-BAL-FORMULA; missing → 0 |
| History | Current state for balance; optional history cap 20 (A-BOOK-HIST) |
| Mechanism | **EG-3:** batch get `booking` by account ID; app formula; missing → 0 |

### AP-C360-4 — Product description for UI

| Attribute | Value |
|---|---|
| Lookup input | (none at runtime) |
| Data read | `accounts.productDesc` already loaded in AP-C360-2 |
| Missing / empty description | Omit account from assembled response |
| Mechanism | **Denormalized on EG-2 account**; EG-4 `products` used at ingest/Admin only |

### AP-C360-5 — Assemble Customer 360 response

| Attribute | Value |
|---|---|
| Input | Customer ID |
| Behavior | Orchestrate AP-C360-1..3; use embedded productDesc; best-effort; INR; 2 d.p. |
| Mechanism | Application only |

---

## Admin / load-lab paths

### AP-ADMIN-1 — Read inventory totals

| Attribute | Value |
|---|---|
| Data read | customerCount, accountCount (+ optional per-line counts) |
| Exactness / freshness | Exact maintained counters; fresh after updating op (A-INVENTORY) |
| Constraint | No full scan on Admin refresh |
| Mechanism | **EG-5:** PK get `inventory`/`totals` (checkpointed updates at ingest) |

### AP-ADMIN-2 — Read load at target Read TPS

| Attribute | Value |
|---|---|
| Ops | Customer 360 assembly (AP-C360-5) against seeded ID range |
| Max target | 5000 TPS |
| Metrics | Feed AP-ADMIN-4 |

### AP-ADMIN-3 — Write load at target Write TPS

| Attribute | Value |
|---|---|
| Ops | W1 customer `lastTouchAt` update; W2 one booking bucket overwrite; 50/50; ≤1 KB (A-WRITE-MIX) |
| Max target | 5000 TPS |
| Kill-switch | Stop all load workers |
| Metrics | Feed AP-ADMIN-4 |
| Mechanism | W1 touches EG-1; W2 touches EG-3 |

### AP-ADMIN-4 — Metrics stream

| Attribute | Value |
|---|---|
| Transport | WebSocket |
| Series | Achieved read/write TPS; latency p50 / p99 / p99.9 |
| Window | User-selectable (e.g. 5 / 15 min) |
| Mechanism | Application metrics (not Aerospike-primary) |

### AP-ADMIN-5 — Ingestion simulation (new)

| Attribute | Value |
|---|---|
| Actor | Admin UI (admin credential) |
| Input | `targetCustomerCount` (and implied ~2 accounts/customer) |
| Behavior | Generate and write customers, accounts, booking, products; update inventory counters |
| Scale | Shared/demo env for ≥5M; smaller counts allowed for laptop |
| Mechanism | Application seeder + EG-1..EG-5 write paths |

---

## Coverage

| Path | Clarification | Design group |
|---|---|---|
| AP-C360-1 | Closed | EG-1 |
| AP-C360-2 | Closed | EG-2 |
| AP-C360-4 | Closed (embed) | EG-2 field + EG-4 catalog |
| AP-C360-3 | Closed | EG-3 |
| AP-C360-5 | Closed | App |
| AP-ADMIN-1 | Closed | EG-5 |
| AP-ADMIN-2..4 | Closed | App (+ EG data) |
| AP-ADMIN-5 | Closed | App + EG-1..5 |
