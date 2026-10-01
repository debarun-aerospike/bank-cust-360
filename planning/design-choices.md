# Customer 360: Design Choices Review

**Reviewed artifact:** `docs/modeling/customer-360-schema-summary.md`  
**Authoritative detail:** `docs/modeling/customer-360-schema-guide.md`  
**Rubric:** `AGENTS.md` mandatory review checks + Aerospike skill failure-mode tests  
**Date:** 2026-10-01  
**Verdict:** **Accept** — choices match access patterns; no blockers for Gate 3 (cluster + seed).

---

## Scope

This review evaluates the condensed schema contract (sets, keys, bins, caps, indexes, C360 read shape). It does not redesign the model. Where the summary is silent, judgments use the approved schema guide.

---

## Choice-by-choice review

### 1. Single namespace `bank`, persistent / never-expire

| Aspect | Assessment |
|---|---|
| Choice | One namespace for customers, accounts, booking, products, inventory |
| Why it fits | Uniform retention; one ops slice; demo does not need per-entity TTL or mixed SC/AP at namespace level |
| Risk | Cannot expire catalog independently of accounts without a later namespace split |
| Status | **Accept** — reopen if TTL or consistency must differ by entity class |

### 2. Six sets driven by access paths (not product-line ER tables)

| Set | Role in access paths | Not merely a noun map |
|---|---|---|
| `customers` | AP-C360-1 / W1 | Profile + touch only |
| `cust_accts` | AP-C360-2 entry | Known-key linkage; avoids SI on owner |
| `accounts` | Batch after linkage | Canonical row + embedded UI text |
| `booking` | AP-C360-3 / W2 | Write isolation from account profile |
| `products` | Ingest / Admin SoT only | Explicitly off C360 read path |
| `inventory` | AP-ADMIN-1 | Counters instead of scan |

**Reject correctly avoided:** one set per Savings / FD / Loan / Card source table; monolithic “customer 360 document.”

**Status:** **Accept** — granularity follows reads/writes, not the relational source list.

### 3. Primary keys: customer string, account prefix+digits, shared booking key

| Key | Choice | Assessment |
|---|---|---|
| Customer | 7-digit zero-padded string | Stable PK for login; Customer No. = key (no alias bin) |
| Account / booking | `{S\|F\|L\|C}` + 12 digits | Line encoded in key; booking co-keyed for batch align |
| Product | Product code | Low cardinality catalog |
| Inventory | `totals` (+ optional ingest shards) | Admin PK get; shards only during parallel seed |

**Status:** **Accept** — every routine path has a known key or a bounded key list from a prior get.

### 4. Split `accounts` + `cust_accts` (not embed full accounts on customer)

| Tradeoff | Detail |
|---|---|
| Cost | Extra PK get + batch ≤5 vs single customer document |
| Benefit | Joint ownership (max 3) without multi-copy account blobs; account attribute writes stay on one key |
| Cap | `acctIds` max **5**; `ownerIds` max **3** — reject on overflow |

**Status:** **Accept** — justified by joint accounts + PK preference over secondary index.

### 5. Embed `productDesc` on `accounts`; keep `products` off the C360 path

| Tradeoff | Detail |
|---|---|
| Cost | Catalog rename needs account backfill or re-ingest |
| Benefit | Removes runtime product fetch and product-code hot keys under Read TPS |
| Guide note | Stakeholder amendment 2026-09-29 |

**Status:** **Accept** — deliberate denormalization for the home-screen assemble path.

### 6. Separate `booking` with flat paise bins (not buckets on `accounts`)

| Tradeoff | Detail |
|---|---|
| Cost | Second batch get (≤5) per C360 |
| Benefit | W2 overwrites one bucket without rewriting account profile |
| Types | S/F: `ledger`/`hold`/`float`; L/C: `principal`/`interest`; optional `hist` max **20** (trim oldest) |
| Compute | App-side formulas; missing bins → balance 0 |

**Status:** **Accept** — write/read isolation matches the Admin write mix; flat bins favor single-bin `operate` over map RMW.

### 7. No secondary indexes on routine paths

Summary states indexes: none. C360 is PK + bounded batch only. Inventory is maintained counters, not scan/SI.

**Status:** **Accept** — index dependence check passes; do not add SI “for owner” while max accounts = 5.

### 8. Inventory `totals` via checkpoint / rollup (not per-record increment)

| Tradeoff | Detail |
|---|---|
| Cost | Counters lag between checkpoints; possible shard sum until rollup |
| Benefit | Avoids hot key `totals` during ≥5M ingest |
| Steady state | W1/W2 do not create/delete entities → Admin poll stays one PK get |

**Status:** **Accept** — hot-key mitigation is part of the contract, not an implementation afterthought.

### 9. C360 read shape (summary ops list)

1. get `customers`  
2. get `cust_accts`  
3. batch get `accounts` (≤5)  
4. batch get `booking` (≤5)  
5. assemble + compute balances in app  

**Assessment:** Bounded fan-out; no product join; best-effort multi-record assembly matches confirmed consistency. Multi-record ingest linkage is not a single Aerospike transaction — already documented as demo-acceptable.

**Status:** **Accept**.

---

## Mandatory review checks (AGENTS.md)

| # | Check | Result | Evidence from summary |
|---|---|---|---|
| 1 | Entity-list mapping | **Pass** | Sets serve linkage, booking write isolation, ingest catalog, inventory — not 1:1 with every banking noun |
| 2 | Index dependence | **Pass** | “None on routine paths”; C360 is PK + batch |
| 3 | CDT misuse | **Pass** | Caps on lists; booking current state is flat bins for W2 |
| 4 | Bins as columns | **Pass** | Fixed bin names per set; inventory line counts are fixed bins, not per-product bins |
| 5 | Accidental normalization | **Pass** | `productDesc` embedded; booking split is intentional for W2, not a pure assemble join |
| 6 | Unbounded growth | **Pass** | Caps 5 / 3 / 20 with reject or trim |
| 7 | Tiny-record overhead | **Pass** | Small records accepted; not collapsed into one hot aggregate |

---

## Aerospike failure-mode spot checks

| Failure mode | Detection against this summary |
|---|---|
| Sets from ER only | **No** — product lines share `accounts`; booking and `cust_accts` are access-path artifacts |
| SI as default access | **No** |
| Client RMW of collections as the design | **No** for W2; linkage appends are bounded CDT ops (guide) |
| Growing bin counts | **No** |
| Extra fetch only to join display text | **Mitigated** via `productDesc` |
| Unbounded CDTs | **No** — explicit overflow table |
| Tiny entities with no sizing stance | **Addressed** — small fixed records; inventory deliberately not per-event hot aggregate |

---

## Residual risks (non-blocking)

1. **Best-effort consistency** across `accounts` / `cust_accts` / `booking` under concurrent W2 and C360 — accepted for demo; document per-key batch miss handling in implementation.
2. **Stale `productDesc`** after catalog edits until backfill — accepted; reopen if instant global rename is required.
3. **Inventory drift** vs true set sizes if checkpoints fail — reconciliation is exceptional (scan), not Admin refresh.
4. **Gate 3 config:** namespace `bank` and never-expire TTL must exist in the Enterprise lab config; summary alone does not provision them.

---

## Summary judgment

The schema summary is a coherent Aerospike contract: known keys, bounded batches, deliberate denormalization where it removes hot joins, write-isolated booking, capped CDTs, and scan-free inventory. Design choices are approved for implementation planning (Gate 3+). Change the schema guide first if any choice above is reopened; regenerate the summary from the guide — do not edit the summary alone.
