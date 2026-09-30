# Customer 360 + Admin Load Lab: Schema Guide

**Authoritative model document.** Update this guide first; regenerate any schema summary from it later.  
**Clarification:** `docs/modeling/customer-360-clarifications.md` (closed)  
**Access patterns:** `docs/modeling/customer-360-access-pattern-matrix.md`  
**Entity groups:** `docs/modeling/customer-360-entity-group-plan.md`

## Document status

| Section | Status |
|---|---|
| EG-1 Customer master | **Approved** |
| EG-2 Accounts | **Approved** (embed `productDesc`) |
| EG-3 Booking | **Approved** |
| EG-4 Product catalog | **Approved** |
| EG-5 Inventory | **Approved** (stakeholder, 2026-09-29) |
| Cross-group validation | **Passed** |
| Schema summary | `docs/modeling/customer-360-schema-summary.md` (in sync) |
| Gate 2 modeling | **Complete** — Gate 3 (cluster + seed) in progress |

No client implementation until EG groups needed for the vertical slice are reviewed (per plan Gates 0–2).

---

## Global modeling context (shared)

### Namespace

| Item | Choice | Rationale |
|---|---|---|
| Namespace | `bank` | Single product domain; all entities share **persistent** retention and one ops slice (clarification: persistent, Enterprise demo) |
| Local/lab note | Namespace `bank` must be declared in Aerospike Enterprise config used in Gate 3. Do not use illegal names (`default`, `aerospike`, `main`). |

**Rejected:** Separate namespaces per product line — unnecessary ops surface for one demo domain with uniform TTL (none / persistent).

**Reopen when:** Product data must expire while accounts remain, or strong-consistency vs AP must differ by entity class at namespace level.

### Consistency mode

| Item | Choice |
|---|---|
| Application consistency | Best-effort assembly (confirmed) |
| Namespace mode | AP is sufficient for this demo unless Enterprise lab is already configured SC; document actual cluster mode at Gate 3 bring-up. Model does not require cross-record transactions. |

### Secondary indexes / scans

Not introduced in EG-1. Routine Customer 360 and Admin load paths must remain primary-key (and later bounded batch). Inventory uses maintained counters (EG-5), not scan-on-refresh.

---

## EG-1 — Customer master

### 1. Record boundary

**One customer → one record.**

All fields required by AP-C360-1 (and W1 write touch) are read/written together under the login key. Average profile is small; max accounts fan-out is modeled in EG-2, not embedded here (avoids rewriting the customer record on every account link and keeps joint-account ownership on the account side).

**Rejected alternatives:**

| Alternative | Why rejected |
|---|---|
| Embed all accounts in the customer record | Max 5 accounts is small, but joint ownership (max 3 customers) and product-line grouping favor account-side identity in EG-2; also W2 booking writes should not contend on the customer record |
| Split profile vs status records | No separate status access path; over-normalization without benefit |
| Customer ID → Customer No. alias record | Clarification: ID **equals** No. — alias unnecessary |

**Reopen when:** Profile grows large independently of status, or a username→customer path is added (out of scope for this workstream).

### 2. Set and primary key

| Item | Contract |
|---|---|
| Set | `customers` |
| User key | 7-digit Customer ID, stored as a **zero-padded decimal string** of length 7 (e.g. `"0000001"`, `"1234567"`) |
| Key examples | `"0000001"`, `"2500000"`, `"5000000"` |
| Cardinality | ≥ 5,000,000 in shared demo seed; configurable lower for laptop ingestion |
| Distribution | Sequential IDs from ingestion are acceptable for demo; RIPEMD partition distribution still spreads digests. **Skew risk:** low for uniform get-by-id; avoid a single hot “stats” key here (counters belong in EG-5) |
| sendKey | Write policy should **send/store key** so tools and optional reads can return the user key |

**Validation:** Key must match `^[0-9]{7}$`. Reject other lengths in API validation.

### 3. Bins

| Bin | Type | Constraints | Ownership / updates |
|---|---|---|---|
| `salutation` | string | One of `Mr`, `Ms`, `Mrs`, `Mx` | Set at create; rarely updated |
| `name` | string | 1–80 chars, display name | Set at create; rare update |
| `status` | string | `Active` \| `Dormant` | Set at create; admin/seed may change |
| `lastTouchAt` | integer | Epoch milliseconds; optional until first W1 | **W1 load write** and optional login mock touch |

**Not stored as bins:** `customerId` / `customerNo` — identical to user key; API derives both from the key (A-CUST-FIELDS / clarification).

**Rejected:** Growing per-visit bins or unbounded history on the customer record — use `lastTouchAt` only for W1 (≤1 KB write easily satisfied).

### 4. Flat bins vs CDT vs multiple records

**Flat bins only** for EG-1. No CDT on the customer record in v1.

### 5. Example JSON record (logical)

Key: `"0000042"`

```json
{
  "salutation": "Ms",
  "name": "Asha Verma",
  "status": "Active",
  "lastTouchAt": 1759161000000
}
```

### 6. Sizing, growth, updates

| Estimate | Value |
|---|---|
| Record size | ~100–200 bytes typical (well under limits) |
| Update rate | Interactive rare; W1 up to Admin Write TPS share (≤5000 aggregate writes split with W2) |
| Growth | Fixed bin set; no collection growth |
| Overflow | N/A |

### 7. TTL / NSUP

| Item | Choice |
|---|---|
| TTL | **Never expire** (persistent); use TTL `-1` / namespace default never-expire aligned with Gate 3 config |
| NSUP | Not relied on for customer deletion in v1 |

### 8. Access-path mapping (EG-1)

| Path | Operation | Notes |
|---|---|---|
| AP-C360-1 | Primary-key `get` on (`bank`, `customers`, customerId) | Read bins `salutation`, `name`, `status` (and `lastTouchAt` only if needed) |
| AP-ADMIN-3 W1 | Primary-key write/`operate` set `lastTouchAt` | Payload ≪ 1 KB; prefer `operate` touch without rewriting unrelated semantics |
| AP-ADMIN-5 | Primary-key `put` create customers during ingestion | Also increments EG-5 counters (designed later) |
| AP-ADMIN-2 | Uses AP-C360-1 inside assembly | Key picker: uniform random over seeded `[1..N]` zero-padded |

**No secondary index** on `status` for the home path — caller already has Customer ID.

### 9. Hot-key / contention

| Risk | Assessment |
|---|---|
| Single customer under interactive use | Low |
| W1 uniform random across 5M keys | Low hot-key risk |
| Hot key if load picker stuck on one ID | Mitigate in loadgen: enforce random/unique spread |

### 10. Create / read / cleanup walkthrough (developer)

1. **Create (ingestion):** For i in 1..N, `put` key `f"{i:07d}"` with salutation/name/status; bump customer inventory counter (EG-5).
2. **Read (login home):** `get` by Customer ID → map to API customer block; Customer No. = same id string.
3. **Write (W1):** `operate`/`put` update `lastTouchAt` only.
4. **Cleanup:** Demo reset = delete set or re-ingest; no customer-delete cascade specified in v1 (account cleanup in EG-2).

### 11. Failure modes (EG-1)

| Case | Expected |
|---|---|
| Unknown Customer ID | AP-C360-1 miss → API 404; assembly stops |
| Dormant customer | Return profile; accounts still assembled (A-STATUS) |
| Invalid key length | API 422 before Aerospike call |
| W1 on missing customer | Count as write error in load metrics |

### 12. EG-1 assumptions log

| Decision | Alternatives rejected | Evidence to reopen |
|---|---|---|
| Set `customers`, key = 7-digit string | Integer key only; separate cust_no bin | Bank requires non-numeric or longer ids |
| Flat bins + `lastTouchAt` for W1 | Separate activity set | Write mix changes (A-WRITE-MIX) |
| Do not embed accounts | Single document 360 record | Latency budget forces single get (measure later) |
| Namespace `bank` | Use Docker default `test` only | Lab cannot add namespace — then remap name in Gate 3 |

### 13. EG-1 review checkpoint

**Status: approved** (stakeholder proceeded after product-line update, 2026-09-29).

Confirmed:

1. Namespace `bank` + set `customers` + zero-padded 7-digit string keys  
2. Bins: `salutation`, `name`, `status`, `lastTouchAt` only  
3. Customer No. derived from key (not duplicated as a bin)  
4. W1 load write = update `lastTouchAt`  
5. Accounts designed in EG-2 (below)

---

## EG-2 — Accounts and customer linkage

### 1. Record boundaries

Two related record types (same namespace `bank`):

| Record | Purpose |
|---|---|
| **Account** (canonical) | Source of truth for account attributes used on the home row (except balance and product description) |
| **Customer→account index** | Bounded list of account IDs for one customer — enables AP-C360-2 by **known primary key** (Customer No. = Customer ID) |

**Why not one embedded document on the customer?** Joint accounts (max 3 owners) would force multi-customer denormalized copies of every account field change. Canonical account + per-customer ID list keeps a single write for account attributes and a small bounded list update per owner on link/unlink.

**Why not four sets (one per product line)?** Access path is “all accounts for customer,” then UI groups by `productLine`. One `accounts` set avoids multi-set fan-out; prefixes `S`/`F`/`L`/`C` already encode line in the account ID (A-ACCT-ID).

**Why not secondary index on owner?** Max 5 accounts and known customer key make PK get + batch (≤5) strictly preferable to SI for the routine home and load paths.

### 2. Sets and primary keys

#### 2a. Set `accounts`

| Item | Contract |
|---|---|
| Set | `accounts` |
| User key | Account ID string per A-ACCT-ID: `{P}{12-digit}`, `P` ∈ `S`\|`F`\|`L`\|`C` |
| Examples | `S000000000042`, `F000000000007`, `L000000000015`, `C000000000003` |
| Cardinality | ~2 × customer count (avg); ~10M at 5M customers |
| Validation | `^[SFLC][0-9]{12}$` |
| sendKey | Store user key on write |

Product-line mapping from prefix:

| Prefix | `productLine` value | UI label |
|---|---|---|
| `S` | `SAVINGS_CURRENT` | Savings / Current |
| `F` | `TERM_DEPOSIT` | Fixed / Term Deposits |
| `L` | `LOAN` | Loans |
| `C` | `CARD` | Cards |

`productLine` bin must match prefix (enforced by ingestion/API validation).

#### 2b. Set `cust_accts`

| Item | Contract |
|---|---|
| Set | `cust_accts` |
| User key | Same 7-digit zero-padded Customer ID as EG-1 |
| Examples | `"0000042"` |
| Cardinality | One record per customer that has ≥1 account (ingestion may always create the record, including empty list) |
| Purpose | AP-C360-2 entry point |

### 3. Bins

#### 3a. `accounts` bins

| Bin | Type | Constraints | Notes |
|---|---|---|---|
| `productLine` | string | `SAVINGS_CURRENT` \| `TERM_DEPOSIT` \| `LOAN` \| `CARD` | Must match key prefix |
| `currency` | string | Always `INR` in v1 | |
| `acctStatus` | string | `Active` \| `Dormant` \| `Closed` \| `Pledged` \| `Hidden` | Default home filter = `Active` |
| `productCode` | string | Non-empty product code | Catalog key; copied at ingest from EG-4 |
| `productDesc` | string | English; 1–120 chars | **Denormalized for UI** — Customer 360 reads this; empty ⇒ omit account |
| `ownership` | string | `PRIMARY` \| `JOINT` | Account-level; `JOINT` when multiple owners |
| `ownerIds` | list\<string\> | 1–3 elements; each `^[0-9]{7}$` | Bounded CDT; max 3 (clarification) |
| `openedAt` | string | ISO date `YYYY-MM-DD` | Sort/display metadata |

Account ID is the record key (not duplicated as a required bin).

**Amendment (2026-09-29):** `productDesc` is embedded on the account so AP-C360-5 does **not** fetch `products` at read time (avoids product hot keys under Read TPS). EG-4 remains seed/Admin catalog source of truth.

#### 3b. `cust_accts` bins

| Bin | Type | Constraints | Notes |
|---|---|---|---|
| `acctIds` | list\<string\> | 0–**5** account ID strings | **Hard cap 5** (clarification max accounts/customer). Ingestion/API must reject append beyond 5 |

**Invariant:** Every account ID in `acctIds` exists in `accounts`, and this customer ID appears in that account’s `ownerIds`. Joint account ⇒ ID present on each owner’s `cust_accts.acctIds`.

**List order (write-time):** Maintain **PRIMARY accounts before JOINT** (by each account’s `ownership`) so default ordering is cheap; assembler still re-sorts defensively and groups by product line for UI tabs.

### 4. Flat bins vs CDT vs multiple records

| Data | Choice |
|---|---|
| Account scalars (incl. `productDesc`) | Flat bins on `accounts` |
| `ownerIds` | Bounded list CDT (cap 3) |
| `acctIds` | Bounded list CDT (cap 5) |
| Booking / balance | **Not** in EG-2 — EG-3 keyed by account ID |
| Live product join on read | **Rejected** — description embedded (`productDesc`) |

### 5. Example records (logical)

**`cust_accts`** key `"0000042"`:

```json
{
  "acctIds": ["S000000000042", "L000000000015"]
}
```

**`accounts`** key `S000000000042`:

```json
{
  "productLine": "SAVINGS_CURRENT",
  "currency": "INR",
  "acctStatus": "Active",
  "productCode": "SB-REG",
  "productDesc": "Regular Savings Account",
  "ownership": "PRIMARY",
  "ownerIds": ["0000042"],
  "openedAt": "2024-03-12"
}
```

**`accounts`** key `L000000000015` (joint loan):

```json
{
  "productLine": "LOAN",
  "currency": "INR",
  "acctStatus": "Active",
  "productCode": "HL-STD",
  "productDesc": "Standard Home Loan",
  "ownership": "JOINT",
  "ownerIds": ["0000042", "0000043"],
  "openedAt": "2023-11-01"
}
```

(Corresponding `cust_accts` for `"0000043"` also contains `L000000000015`.)

### 6. Sizing, growth, updates

| Estimate | Value |
|---|---|
| `accounts` record size | ~250–450 bytes typical (includes `productDesc`) |
| `cust_accts` record size | ~50–150 bytes (≤5 short IDs) |
| Fan-out per Customer 360 | 1 get (`cust_accts`) + batch get ≤5 (`accounts`) |
| Update rate | Rare for interactive; ingestion heavy; no W2 on these sets (W2 is booking) |
| Growth / overflow | `acctIds` **must not** exceed 5 — reject or require explicit replace policy; `ownerIds` **must not** exceed 3 |

### 7. TTL

Persistent / never-expire (same as EG-1).

### 8. Access-path mapping (EG-2)

| Path | Operations | Notes |
|---|---|---|
| AP-C360-2 | PK `get` `cust_accts` → batch `get` `accounts` for `acctIds` | Coalesce duplicate IDs; inspect per-key batch results |
| AP-C360-5 (partial) | Filter `acctStatus` (default `Active`); sort PRIMARY then JOINT; group by `productLine` in app | Dropdown filter may include other statuses |
| AP-ADMIN-5 | Create `accounts` + append to each owner’s `cust_accts.acctIds` (atomic list append with size check) | Update EG-5 account counters |
| AP-ADMIN-2 | Same as interactive assembly | |
| AP-ADMIN-3 | No direct EG-2 writes in v1 write mix | |

**No secondary index** for “accounts by customer.”

### 9. Relationship maintenance

| Event | Steps (application; best-effort multi-record) |
|---|---|
| Link new account to owners | `put` account; for each ownerId append account ID to `cust_accts` if len\<5; bump counters |
| Joint add owner | Update `ownerIds` + `ownership`; append to new owner’s `acctIds` |
| Unlink / close (demo) | Set `acctStatus` or remove from `acctIds` lists — full cascade policy can stay demo-simple (re-ingest reset) |

Document for implementers: multi-record updates are **not** a single Aerospike transaction in this model; ingestion should write in an order that prefers visible consistency (account before linkage append), and load/read paths tolerate best-effort.

### 10. Hot-key / skew

| Risk | Assessment |
|---|---|
| Customer with 5 accounts | Low — tiny records |
| Popular joint account | Single `accounts` key; max 3 owners updating linkage — low for demo |
| Hot `cust_accts` under read load | Uniform customer ID picker spreads load |

### 11. Create / read walkthrough

1. Ingest customer `0000042` (EG-1).
2. Create account `S000000000042` with `ownerIds=["0000042"]`.
3. `put`/`operate` `cust_accts` `"0000042"` with `acctIds` including that ID.
4. Read path: get `cust_accts` → batch get accounts (incl. `productDesc`) → filter/sort/group → batch get booking (EG-3) → compute balances.

### 12. Failure modes (EG-2)

| Case | Expected |
|---|---|
| Missing `cust_accts` or empty `acctIds` | Customer 360 with empty accounts list (after successful EG-1) |
| Account ID in list but account record missing | Skip that ID (best-effort); optionally metric |
| Batch partial miss | Per-key handling; do not fail entire 360 unless policy changes |
| Append would exceed 5 accounts | Reject write; ingestion must honor max |
| Product code unresolved / empty `productDesc` | Omit account in assembler |

### 13. EG-2 assumptions log

| Decision | Alternatives rejected | Evidence to reopen |
|---|---|---|
| Split `accounts` + `cust_accts` | Embed full accounts on customer; SI on owner | Joint ownership + PK preference; measure if single-get embedding wins latency |
| One `accounts` set for all four lines | Four product-line sets | No per-line isolated access path |
| Bounded `acctIds` list cap 5 | Unbounded list; query | Clarified max 5 |
| Denormalize only IDs on customer, not full account fields | Duplicate account blobs per owner | Avoid multi-copy field updates |
| Embed `productDesc` on account | Live get/batch from `products` on every C360 | Read-path latency + product hot keys under load; reopen if catalog renames must be instant across all accounts |

### 14. EG-2 review checkpoint

**Status: approved** (stakeholder, 2026-09-29), **amended** to embed `productDesc`.

Confirmed:

1. Sets `accounts` (key = `S|F|L|C` + 12 digits) and `cust_accts` (key = customer ID)  
2. AP-C360-2 = get linkage + batch get ≤5 accounts (no secondary index)  
3. Bins as specified incl. **`productDesc`**; `ownerIds` cap 3; `acctIds` cap 5  
4. Product lines `SAVINGS_CURRENT` \| `TERM_DEPOSIT` \| `LOAN` \| `CARD`  
5. Booking in EG-3; product **catalog** in EG-4 (not on C360 read path)  

---

## EG-4 — Product catalog (ingest / Admin SoT)

### 1. Record boundary

**One product code → one catalog record** used at **ingestion and Admin catalog maintenance**.

Customer 360 **does not** read this set at runtime. English description required by the UI is **copied onto** `accounts.productDesc` when the account is created (or when Admin deliberately refreshes descriptions).

**Why keep the set at all?** Gives AP-ADMIN-5 a single place to define valid codes, lines, and active flags before copying onto accounts; supports future Admin “edit catalog” without scanning accounts first.

**Why not read it on every C360?** Stakeholder decision 2026-09-29: embed UI product fields on the account to remove join latency and product-code hot keys under Read TPS.

### 2. Set and primary key

| Item | Contract |
|---|---|
| Namespace | `bank` |
| Set | `products` |
| User key | Product **code** string |
| Examples | `SB-REG`, `CA-PREM`, `FD-1Y`, `HL-STD`, `CC-GOLD` |
| Cardinality | Low hundreds for demo |
| Validation | Non-empty; recommend `^[A-Z0-9][A-Z0-9\-_]{1,31}$` |
| sendKey | Store user key on write |

### 3. Bins

| Bin | Type | Constraints | Notes |
|---|---|---|---|
| `description` | string | English; 1–120 chars | Copied to `accounts.productDesc` at account create |
| `productLine` | string | Four product lines | Seed validation |
| `active` | boolean | `true` / `false` | Ingest must **not** create accounts for `active=false` |

### 4. Example

Key: `SB-REG`

```json
{
  "description": "Regular Savings Account",
  "productLine": "SAVINGS_CURRENT",
  "active": true
}
```

### 5. Access-path mapping (EG-4)

| Path | Operation | Notes |
|---|---|---|
| AP-C360-4 (runtime) | **None** — satisfied by `accounts.productDesc` | Empty `productDesc` ⇒ omit account |
| AP-ADMIN-5 | Read/put catalog; copy `description` → account at create | |
| Catalog rename (optional Admin) | Update `products` then batch-update affected `accounts.productDesc` | Rare; demo may skip and rely on re-ingest |

### 6. EG-4 assumptions log

| Decision | Alternatives rejected | Evidence to reopen |
|---|---|---|
| Embed description on account; catalog offline to C360 reads | Live batch get products every C360 | Instant global rename without account backfill required |
| Retain `products` set for ingest | Delete catalog entirely | Need Admin validation of codes |

### 7. EG-4 review checkpoint

**Status: approved** with embed decision (stakeholder, 2026-09-29).

---

## EG-3 — Booking buckets and balance inputs

### 1. Record boundary

**One account → one booking record** keyed by the same Account ID.

Current bucket amounts live here — **not** on `accounts` — so AP-ADMIN-3 **W2** (high-rate bucket overwrite) does not rewrite the account profile record and does not contend with account attribute reads on the same key.

Home-screen balance uses **current** buckets only (A-BOOK-HIST). Optional history is a **bounded** list (cap **20**).

### 2. Set and primary key

| Item | Contract |
|---|---|
| Namespace | `bank` |
| Set | `booking` |
| User key | Same as `accounts` key: `^[SFLC][0-9]{12}$` |
| Examples | `S000000000042`, `L000000000015` |
| Cardinality | ≈ account count |
| sendKey | Store user key on write |

### 3. Bins

Amounts are stored as **integer paise** (INR × 100) to avoid float drift. API converts to decimal rupees for display (2 d.p., round half away from zero).

#### 3a. Savings/Current and Fixed/Term (`S`, `F`)

| Bin | Type | Meaning |
|---|---|---|
| `ledger` | integer | Ledger balance (paise) |
| `hold` | integer | Holds (paise), ≥ 0 |
| `float` | integer | Float / uncleared (paise), ≥ 0 |
| `hist` | list\<map\> (optional) | Cap **20**; each element `{ "ts": epochMs, "ledger": n, "hold": n, "float": n }` |

**Required for balance:** `ledger`, `hold`, `float`. Any missing → balance **0** (clarification).

#### 3b. Loan and Card (`L`, `C`)

| Bin | Type | Meaning |
|---|---|---|
| `principal` | integer | Principal outstanding (paise), ≥ 0 |
| `interest` | integer | Interest outstanding (paise), ≥ 0 |
| `hist` | list\<map\> (optional) | Cap **20**; `{ "ts", "principal", "interest" }` |

**Required for balance:** `principal`, `interest`. Any missing → balance **0**.

Do **not** store unrelated bucket bins on a record (no `ledger` on a loan record). Product line is implied by account ID prefix; assembler already knows `productLine` from EG-2.

### 4. Balance formulas (application)

| Product line | Balance (paise) | Display |
|---|---|---|
| `SAVINGS_CURRENT`, `TERM_DEPOSIT` | `ledger - hold - float` | Rupees, 2 d.p. |
| `LOAN`, `CARD` | `principal + interest` | Rupees, 2 d.p. (amount owed) |

### 5. Flat bins vs CDT

| Data | Choice |
|---|---|
| Current buckets | **Flat integer bins** — W2 updates one bin via `operate` without read-modify-write of a map |
| History | Optional bounded **list** CDT, cap 20; trim on append |

**Rejected:** Embed buckets on `accounts` — couples W2 write load to account profile I/O.  
**Rejected:** Unbounded history — violates CDT bound rules (A-BOOK-HIST).

### 6. Example records

**`booking`** key `S000000000042`:

```json
{
  "ledger": 12500050,
  "hold": 50000,
  "float": 0,
  "hist": []
}
```

→ available = 12450050 paise → display ₹124,500.50

**`booking`** key `L000000000015`:

```json
{
  "principal": 250000000,
  "interest": 1250000,
  "hist": []
}
```

→ owed = 251250000 paise → display ₹2,512,500.00

### 7. Sizing, growth, updates

| Estimate | Value |
|---|---|
| Record size | ~50–200 bytes without history; history ≤20 small maps still modest |
| Read pattern | Batch get ≤5 booking keys per Customer 360 (same IDs as accounts) |
| Write pattern | W2: overwrite one bucket bin on random account; ≤1 KB |
| Overflow | `hist` trim to 20 on append; never unbounded |

### 8. TTL

Persistent / never-expire.

### 9. Access-path mapping (EG-3)

| Path | Operation | Notes |
|---|---|---|
| AP-C360-3 | Batch `get` `booking` for account IDs from EG-2 | Parallel with nothing else required after account IDs known; can run after accounts batch |
| AP-C360-5 | Compute balance in app; missing booking or required bin → **0** | |
| AP-ADMIN-3 W2 | `operate`/`put` one of `ledger`\|`hold`\|`float` or `principal`\|`interest` | Choose bin legal for account prefix; optionally append trimmed hist |
| AP-ADMIN-5 | Create booking with each account | |

**No secondary index.**

### 10. Hot-key / contention

| Risk | Assessment |
|---|---|
| W2 uniform over account IDs | Low if picker is uniform |
| Same account as interactive C360 | Occasional contention; best-effort OK |
| Hist append under W2 | Optional — prefer W2 **not** append hist every time under load (current bins only) to keep writes tiny |

### 11. Create / read / write walkthrough

1. After account create, `put` matching `booking` with required bins.  
2. C360: batch get booking for visible accounts → formula → display.  
3. W2: pick random seeded account ID → set one legal bucket bin to a new paise value.

### 12. Failure modes (EG-3)

| Case | Expected |
|---|---|
| No booking record | Balance 0 |
| Partial bins | Balance 0 |
| W2 on wrong bin for product line | Count write error; do not create illegal bins |
| Hist would exceed 20 | Trim oldest |

### 13. EG-3 assumptions log

| Decision | Alternatives rejected | Evidence to reopen |
|---|---|---|
| Separate `booking` set by account ID | Buckets on `accounts` | W2 vs profile contention; measure if single-record wins |
| Integer paise | Float/double bins | Display/rounding bugs |
| Flat bucket bins | Single map CDT of buckets | W2 single-bin operate clarity |
| Hist optional; W2 skips hist under load | Always append hist | Write amplification at 5k Write TPS |

### 14. EG-3 review checkpoint

**Status: approved** (stakeholder, 2026-09-29).

Confirmed:

1. Set `booking`, key = account ID  
2. Paise integers; formulas as specified; missing → 0  
3. Flat bins per product-line family; optional `hist` cap 20  
4. W2 updates booking only  
5. Product description on `accounts.productDesc`  

---

## EG-5 — Inventory counters

### 1. Record boundary

**Maintained counter record(s)** for Admin inventory (AP-ADMIN-1). Not derived by scanning `customers` / `accounts`.

Admin needs at least: total customers, total accounts; optional per product-line account counts and product catalog count.

### 2. Hot-key design (critical for ≥5M ingest)

A naive `operate` increment on **one** key per customer/account create would make `totals` a severe hot key during bulk ingestion.

| Choice | Detail |
|---|---|
| Display record | Single key `totals` in set `inventory` — what Admin UI reads |
| Update strategy | **Seeder / ingest job** keeps in-process counters and **writes `totals` on a checkpoint cadence** (e.g. every 10 000 customers) and **once at job end** — not once per record |
| Parallel workers (optional) | Each worker writes `totals:w{N}` shards; Admin read **sums** shards **or** a final rollup copies into `totals`. Prefer rollup-to-`totals` at job end so the steady-state Admin path is one PK get |

**Rejected:** Increment `totals` on every account create under multi-threaded ingest.  
**Rejected:** Full set scan / info statistics as the Admin refresh path (A-INVENTORY).

W1/W2 load mix does **not** create/delete customers or accounts, so steady-state Admin load does not hammer counters. Only ingestion (AP-ADMIN-5) updates them.

### 3. Set and primary key

| Item | Contract |
|---|---|
| Namespace | `bank` |
| Set | `inventory` |
| Primary Admin key | `totals` |
| Optional shard keys | `totals:w0` … `totals:w{K-1}` during parallel ingest only |
| sendKey | Store user key on write |

### 4. Bins (all integer counters ≥ 0)

Bin names ≤ 15 characters:

| Bin | Meaning |
|---|---|
| `custCnt` | Total customers |
| `acctCnt` | Total accounts |
| `acctS` | Accounts with prefix `S` (Savings/Current) |
| `acctF` | Accounts with prefix `F` (Fixed/Term) |
| `acctL` | Accounts with prefix `L` (Loans) |
| `acctC` | Accounts with prefix `C` (Cards) |
| `prodCnt` | Product catalog entries (optional; updated when catalog seeded) |
| `updatedAt` | Epoch ms of last counter write (optional freshness signal) |

Invariant for a consistent snapshot after rollup: `acctCnt == acctS + acctF + acctL + acctC`.

### 5. Example record

Key: `totals`

```json
{
  "custCnt": 5000000,
  "acctCnt": 10000000,
  "acctS": 4000000,
  "acctF": 2000000,
  "acctL": 2500000,
  "acctC": 1500000,
  "prodCnt": 24,
  "updatedAt": 1759161600000
}
```

### 6. Flat bins vs CDT

**Flat integer bins only.** No collections.

### 7. TTL

Persistent / never-expire.

### 8. Access-path mapping (EG-5)

| Path | Operation | Notes |
|---|---|---|
| AP-ADMIN-1 | PK `get` (`bank`, `inventory`, `totals`) | No scan; low QPS |
| AP-ADMIN-5 | Checkpoint/`put` or `operate` add on `totals` (or shards then rollup) | Exact relative to successful counter writes |
| Customer 360 | Does not read inventory | |

### 9. Failure modes (EG-5)

| Case | Expected |
|---|---|
| Missing `totals` | Admin shows zeros or “not seeded” |
| Drift vs real set sizes | Re-ingest or run one-off reconciliation (exceptional scan — not on Admin poll) |
| Parallel shard without rollup | Admin may sum shards if documented; prefer rollup |

### 10. EG-5 assumptions log

| Decision | Alternatives rejected | Evidence to reopen |
|---|---|---|
| Checkpointed / rolled-up `totals` | Per-record increments | Hot key during 5M ingest |
| Optional line breakdown bins | Customers+accounts only | Admin optional breakdowns are cheap once writing totals |
| No SI / no scan on refresh | info/scan counts | A-INVENTORY |

### 11. EG-5 review checkpoint

**Status: approved** (stakeholder, 2026-09-29).

Confirmed:

1. Set `inventory`, Admin key `totals`  
2. Checkpointed updates during ingest (not per-record)  
3. Bins `custCnt`, `acctCnt`, `acctS/F/L/C`, optional `prodCnt`, `updatedAt`  
4. Steady-state W1/W2 do not touch inventory  

---

## Cross-group validation

### Access-path coverage

| Path | Mechanism | Status |
|---|---|---|
| AP-C360-1 | PK get `customers` | Covered EG-1 |
| AP-C360-2 | PK get `cust_accts` + batch get `accounts` | Covered EG-2 |
| AP-C360-3 | Batch get `booking` | Covered EG-3 |
| AP-C360-4 | `accounts.productDesc` (no runtime product get) | Covered EG-2 / EG-4 |
| AP-C360-5 | App assemble + balance formulas | Covered |
| AP-ADMIN-1 | PK get `inventory`/`totals` | Covered EG-5 |
| AP-ADMIN-2 | C360 under rate limit | Covered |
| AP-ADMIN-3 | W1 `customers.lastTouchAt`; W2 `booking` bin | Covered EG-1 / EG-3 |
| AP-ADMIN-4 | WebSocket metrics (app) | Covered |
| AP-ADMIN-5 | Seed all sets + inventory checkpoints | Covered |

**End-to-end C360 I/O (typical):** 1 customer get + 1 cust_accts get + ≤5 accounts batch + ≤5 booking batch. **No SI. No product get.**

### Mandatory review checks (AGENTS.md)

| Check | Result |
|---|---|
| 1. Entity-list mapping | **Pass** — sets follow access paths (`cust_accts` linkage, `booking` split for W2), not 1:1 with every noun only; `products` retained for ingest SoT despite embed |
| 2. Index dependence | **Pass** — zero secondary indexes on routine paths |
| 3. CDT misuse | **Pass** — bounded `acctIds`/`ownerIds`/`hist`; W2 uses flat bin operate not client RMW of maps |
| 4. Bins as columns | **Pass** — fixed bin schemas; no per-data bin growth |
| 5. Accidental normalization | **Pass** — `productDesc` embedded; booking separate for write isolation (intentional extra fetch, ≤5 batch) |
| 6. Unbounded growth | **Pass** — caps 5 accounts, 3 owners, hist 20 |
| 7. Tiny-record overhead | **Pass** — small records accepted; not collapsed into one hot aggregate for customers/accounts |

### Hot-key / skew summary

| Key class | Risk | Mitigation |
|---|---|---|
| Customer / account / booking under uniform loadgen | Low | Random ID picker |
| Popular product code | Mitigated | No runtime product reads |
| `inventory`/`totals` | High if per-record incr | Checkpoint / shard+rollup only at ingest |

### Open operational notes (Gate 3+)

- Declare namespace `bank` in Enterprise Aerospike config  
- Default TTL never-expire / persistent  
- Schema summary must stay derived from this guide  

### Cross-group validation status

**Passed** (EG-1–EG-5 approved, 2026-09-29). Gate 2 data-model vertical slice is complete. Next: Gate 3 local Aerospike + seed (`ops/`).
