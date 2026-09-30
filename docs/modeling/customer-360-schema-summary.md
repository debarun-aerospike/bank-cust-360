# Customer 360 + Admin Load Lab: Schema Summary

**Derived from** `docs/modeling/customer-360-schema-guide.md` — do not edit independently.  
**Namespace:** `bank` (persistent / never-expire; configure in Enterprise lab)  
**Status:** Final (derived from approved schema guide after EG-5 / Gate 2 close)  

## Sets

### `customers`

| Item | Contract |
|---|---|
| Key | 7-digit zero-padded string (`0000001`) |
| Purpose | Customer master (AP-C360-1, W1) |
| Bins | `salutation` (str), `name` (str), `status` (`Active`\|`Dormant`), `lastTouchAt` (int ms) |

### `cust_accts`

| Item | Contract |
|---|---|
| Key | Same as customer ID |
| Purpose | Customer → account ID list (AP-C360-2) |
| Bins | `acctIds` (list\<str\>, **max 5**) |

### `accounts`

| Item | Contract |
|---|---|
| Key | `{S\|F\|L\|C}` + 12 digits |
| Purpose | Canonical account + embedded UI product text |
| Bins | `productLine`, `currency` (`INR`), `acctStatus`, `productCode`, `productDesc`, `ownership` (`PRIMARY`\|`JOINT`), `ownerIds` (list, **max 3**), `openedAt` |

`productLine`: `SAVINGS_CURRENT` \| `TERM_DEPOSIT` \| `LOAN` \| `CARD`

### `booking`

| Item | Contract |
|---|---|
| Key | Same as account ID |
| Purpose | Balance buckets (AP-C360-3, W2) |
| Bins (S/F) | `ledger`, `hold`, `float` (int paise); optional `hist` (list, **max 20**) |
| Bins (L/C) | `principal`, `interest` (int paise); optional `hist` (max 20) |

**Balance:** S/F → `ledger - hold - float`; L/C → `principal + interest`; missing → 0. Display: INR, 2 d.p.

### `products`

| Item | Contract |
|---|---|
| Key | Product code |
| Purpose | Catalog SoT for ingest/Admin (**not** on C360 read path) |
| Bins | `description`, `productLine`, `active` (bool) |

### `inventory`

| Item | Contract |
|---|---|
| Key | `totals` (Admin); optional `totals:w{N}` during parallel ingest |
| Purpose | AP-ADMIN-1 counts without scan |
| Bins | `custCnt`, `acctCnt`, `acctS`, `acctF`, `acctL`, `acctC`, `prodCnt`, `updatedAt` |
| Update rule | Checkpoint / rollup during AP-ADMIN-5 — **not** per-record under ingest |

## Indexes

None on routine paths.

## Growth / overflow triggers

| Collection | Cap | On overflow |
|---|---|---|
| `cust_accts.acctIds` | 5 | Reject append |
| `accounts.ownerIds` | 3 | Reject append |
| `booking.hist` | 20 | Trim oldest |

## Customer 360 read shape (ops)

1. get `customers`  
2. get `cust_accts`  
3. batch get `accounts` (≤5)  
4. batch get `booking` (≤5)  
5. assemble + compute balances (app)
