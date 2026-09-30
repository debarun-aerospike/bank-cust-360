# Customer 360 + Admin Load Lab: Clarification Document

## Status

- Phase: Gate 1 — **closed** (2026-09-29)
- Clarification gate: **closed**
- Schema design: **Gate 2 complete** (EG-1–EG-5 approved)
- Next: Gate 5 Next.js UI; Gate 4 backend at `backend/`
- Client / application implementation: not started
- Related plan: `planning/customer-360-netbanking-plan.md` (Gate 0 accepted)
- Relationship to `docs/modeling/banking-customer-profile-clarifications.md`: **separate workstream**
- UI style note: `planning/UI-styles.md` — `#F8F413`, `#0D1B32`, `#F2F1ED` / white

No namespace/set/key/bin design is selected **in this clarification document**; those live in the schema guide starting with EG-1.

## Confirmed requirements (stakeholder answers)

Sources: plan + stakeholder answers inline on 2026-09-29.

### Identity and eligibility

| Topic | Confirmed value |
|---|---|
| Customer ID | **7-digit** identifier; **unique** per customer |
| Customer No. | **Same value as Customer ID** (1:1 identity) |
| Customer status values | `Active`, `Dormant` |
| Joint accounts | Yes; **max 3 owners** per account |
| Home currency | **INR only**; no FX on home screen |

### Account universe and UI

| Topic | Confirmed value |
|---|---|
| Product lines | **`SAVINGS_CURRENT`** (Savings/Current), **`TERM_DEPOSIT`** (Fixed/Term Deposits), **`LOAN`**, **`CARD`** (replaces former single Deposits + Trade lines) |
| Accounts per customer | Average **2**, p99 **2**, maximum **5** |
| Default home-screen accounts | Filtered; closed / dormant / pledged / hidden appear **only if user selects** from a dropdown |
| Account ordering | **Primary** accounts first, then **joint** accounts |
| UI grouping | **Group by product line** — separate sections or tabs (**Savings/Current**, **Fixed/Term Deposits**, **Loans**, **Cards**) |
| Product key | Product **code** |
| Product description locale | **English** |
| Missing / retired product | **Omit the account** from the response |

### Balance / booking behavior

| Topic | Confirmed value |
|---|---|
| Missing / partial / inconsistent buckets | Show balance **0** |
| Decimal display | **2** decimal places; round half away from zero (“round to next”) for display |
| Data retention | **Persistent** (customer, account, booking, product) — no TTL expiration for demo data |

### Consistency, platform, auth, Admin

| Topic | Confirmed value |
|---|---|
| Response consistency | **Best-effort** stitching across sources is acceptable |
| Latency SLO | Demo-grade: whatever the Docker / lab environment can sustain (no hard p99 SLA) |
| Aerospike edition | **Enterprise** |
| Simulated login | **Mock** token / session |
| Admin access | Gated by **admin credential** |
| Load mix guidance | **80% reads / 20% writes** when both are active; max payload **1 KB** per write |
| Max Admin TPS | Read **5000**, Write **5000**; kill-switch **stops** load; no hard worker concurrency cap |
| Metrics | **WebSocket**; user-selectable chart window (e.g. 5 / 15 min); chart **p50 / p99 / p99.9** |
| Large seed (≥5M) | **Shared / demo environment only**; ingestion count **configurable** at load time |
| Ingestion UX | **Admin screen for ingestion simulation** (new requirement) |
| Frontend | **Next.js** |
| Backend | **FastAPI** |
| Seed accounts | Average **2** accounts/customer → about **10M accounts** at 5M customers; per-customer max **5** |

### Still-minimum response fields

No additional home-screen fields were requested beyond:

- Customer: customerId, customerNo, salutation, name, status
- Account row: accountId, productLine, currency, accountStatus, productDescription, balance

## Approved assumptions (stakeholder asked for suggestions)

Reconsider when the trigger fires. These are required to close Gate 1 and design records.

| ID | Assumption | Reconsider when |
|---|---|---|
| A-STATUS | **Active** customers only may use Customer 360 / netbanking login. **Dormant** customers are rejected at the API (403). Default **account** filter on home screen = accounts with status `Active` only; dropdown can include `Dormant`, `Closed`, `Pledged`, `Hidden`. Seed keeps customer status and account status aligned. | Product wants Dormant customers to view read-only C360, or different default account filter |
| A-ACCT-ID | Account IDs are **globally unique** across product lines. Format: `{P}{12-digit}` where `P` ∈ `S` / `F` / `L` / `C` (**S**avings/Current, **F**ixed/Term Deposit, **L**oan, **C**ard), e.g. `S000000000042`. Max length 13. Immutable after open. | Bank already has a different account numbering scheme |
| A-ACCT-FIELDS | Beyond currency, status, product code, each account carries: `accountId`, `productLine` ∈ {`SAVINGS_CURRENT`,`TERM_DEPOSIT`,`LOAN`,`CARD`}, `ownership` (`PRIMARY`\|`JOINT`), `ownerCustomerIds` (1–3 customer IDs), `openedAt` (ISO date). Currency always `INR`. | More banking fields required on home or load writes |
| A-BUCKETS | Bucket codes (amounts in INR; schema guide picks storage type): **Savings/Current and Fixed/Term Deposit:** `ledger`, `hold`, `float`. **Loan and Card:** `principal`, `interest`. | Bank provides official bucket chart of accounts |
| A-BAL-FORMULA | **Savings/Current and Fixed/Term available balance** = `ledger - hold - float`. **Loan and Card balance (amount owed)** = `principal + interest` (positive outstanding). If any required bucket missing → balance **0** (confirmed Q15). | Official available vs ledger rules differ |
| A-BOOK-HIST | Home-screen balance uses **current** bucket state only. Optional booking history, if stored, is capped at **20 entries** (preferred over rolling 1 calendar month for demo simplicity). | Need time-travel balances or statement history |
| A-WRITE-MIX | Under Write TPS, each write is ≤1 KB and is one of: **(W1)** update customer bin `lastTouchAt` (epoch ms) on a random seeded customer; **(W2)** overwrite one booking bucket amount on a random seeded account. Load generator splits W1/W2 **50/50**. Combined with Read TPS, demo guidance remains ~80/20 read/write volume when both targets are set proportionally. | Compliance forbids mutating booking in lab, or different write types required |
| A-INVENTORY | Inventory totals use **maintained counter records** updated during seed/ingestion and on account-creating writes. Admin reads counters by primary key (no set scan on refresh). Counts are **exact** relative to successful counter updates; freshness = immediate after the updating operation. | Counters drift and a reconciliation scan is mandated |
| A-INGEST | Admin **ingestion simulation** accepts `targetCustomerCount` (and derived accounts via avg≈2), writes customers/accounts/booking/products, and updates inventory counters. Runs only with admin credential. | Need separate bulk tool only, no UI |
| A-CUST-FIELDS | Salutation ∈ {`Mr`,`Ms`,`Mrs`,`Mx`}; `name` is a single display string ≤80 chars. No other customer profile fields in v1. | KYC/contact fields required on home header |
| A-PROD-EMBED | UI product description is **embedded** on each account as `productDesc` (copied from `products` at ingest). Customer 360 does **not** read `products` at runtime. Empty `productDesc` ⇒ omit account. | Instant catalog-wide rename without account backfill is required |

## Domain vocabulary (updated)

| Concept | Confirmed meaning |
|---|---|
| Customer ID / Customer No. | Same 7-digit unique id |
| Customer status | `Active` \| `Dormant` |
| Account ownership | `PRIMARY` \| `JOINT` (max 3 owners) |
| Product key | Product **code** |
| Product lines | See Account universe — four lines including Cards; Trade removed |
| Buckets | See A-BUCKETS |
| Inventory totals | Maintained counters (A-INVENTORY) |

## Entity and relationship map (logical)

```text
Customer (id = no, 7-digit)
   │
   ├── status ∈ {Active, Dormant}
   │
   └── linked to 1..5 Accounts (avg 2)
            │
            ├── productLine ∈ {SAVINGS_CURRENT, TERM_DEPOSIT, LOAN, CARD}
            ├── ownership PRIMARY|JOINT (≤3 owner customer ids)
            ├── product code → Product (English description); missing product ⇒ omit account
            └── current buckets → Balance (A-BAL-FORMULA); missing ⇒ 0

InventoryCounters → customerCount, accountCount (, optional per product line)
```

## Access patterns

See `docs/modeling/customer-360-access-pattern-matrix.md` (updated for closed clarifications + AP-ADMIN-5 ingestion).

## Entity-group plan

See `docs/modeling/customer-360-entity-group-plan.md`.

## Gate 1 exit criteria

| Criterion | Status |
|---|---|
| Confirmed vs MISSING / assumptions for plan §3 | **Closed** |
| Entity / relationship map | Done |
| Access-pattern matrix | Done (updated) |
| Entity-group plan | Done (updated) |
| Ready to design EG-1 | **Yes** |

## Next step

Gate 2 closed. Follow `ops/README.md` for Gate 3 (Docker Aerospike + seed/verify). Gate 4 (FastAPI) starts after you request application implementation.
