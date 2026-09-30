# Banking Customer Profile Service: Aerospike Model Review

## Review outcome

**Status: BLOCKED — no data model has been submitted.**

The repository contains a clarification document, not a schema guide or draft
model. The clarification document explicitly states that schema design has not
started and that no namespace, set, record boundary, key format, bin, CDT,
index, expression, query, scan, or batch design has been selected.

That is appropriate for the current clarification phase, but it means the
requested design review cannot produce pass/fail conclusions about an actual
model. This report therefore records a structured readiness review. Each item
states what is absent, which access patterns it prevents reviewers from
validating, the consequence, and the alternatives that a future design must
evaluate. No alternative is selected here.

## Material reviewed

- `AGENTS.md`
- `docs/modeling/banking-customer-profile-clarifications.md`
- Installed Aerospike skill and its relevant modeling, CDT, TTL, query, batch,
  record-size, hot-key, and failure-mode rules

## Severity definitions

- **BLOCKER:** A model cannot be validated or approved without this decision.
- **HIGH:** The gap can invalidate correctness, bounded growth, or performance.
- **MEDIUM:** The gap prevents complete operational or efficiency review.

## Access-pattern identifiers

- **AP-1:** Fetch customer profile by customer ID.
- **AP-2:** Fetch all accounts belonging to a customer.
- **AP-3:** Fetch current customer status.
- **AP-4:** Update customer contact information.
- **AP-5:** Add account to customer.
- **AP-6:** Remove account from customer.
- **AP-7:** Fetch customer by username.
- **AP-8:** Fetch recently accessed accounts for customer.

## Structured review

### 1. Access-pattern coverage — BLOCKER

**Specific problem:** AP-1 through AP-8 are inventoried, but their result
shapes, mutation semantics, SLOs, consistency, cardinality bounds, and storage
operation paths remain unresolved. There is no matrix mapping each path to a
record or Aerospike operation.

**Affected access patterns:** AP-1 through AP-8.

**Consequence:** Reviewers cannot determine whether every required path is
served, whether common paths are primary-key operations, or whether one design
decision makes another path slow or incorrect.

**Alternatives to evaluate:**

- Complete the missing requirements and map each path to a known-key single
  record operation, bounded batch, or justified query path.
- Split paths into explicit projections if callers need different payloads.
- Add any missing status-write, recent-access-write, lifecycle, bulk, or
  administrative paths before record design.

No access mechanism is selected by this review.

### 2. Record boundaries — BLOCKER

**Specific problem:** No record boundaries are defined for profile, status,
contact data, accounts, customer-account relationships, username resolution, or
recent-account history.

**Affected access patterns:** AP-1 through AP-8.

**Consequence:** Full-record I/O, atomicity, contention, TTL scope, read fan-out,
and write amplification cannot be estimated. It is also impossible to tell
whether persistent account data would accidentally expire with a profile.

**Alternatives to evaluate:**

- Co-locate fields read and written together in one bounded record.
- Separate data with different TTL, consistency, lifecycle, access frequency,
  or write hotness.
- Use multiple related records when independent access paths or bounded size
  justify the added fan-out.

The choice must follow confirmed access patterns and sizing, not domain nouns.

### 3. Primary-key design — BLOCKER

**Specific problem:** Customer-ID and username inputs are known at a business
level, but no namespace/set/key contract, key format, normalization rule,
distribution analysis, or username-to-customer resolution path exists.

**Affected access patterns:** Directly AP-1 through AP-8; AP-7 has the largest
unresolved inverse-lookup concern.

**Consequence:** The dominant customer-ID workload cannot be proven to use the
fast primary-key path. Username uniqueness, skew, collisions, rename behavior,
and lookup consistency cannot be validated.

**Alternatives to evaluate:**

- Deterministic customer-ID keys for customer-driven paths.
- A deterministic username lookup record when username is a unique identifier.
- A secondary-index query only if AP-7 is genuinely predicate-driven rather
  than resolvable as a known unique key.
- Related or composite keys for bounded relationship slices if a single record
  cannot meet growth or contention requirements.

### 4. Record size — BLOCKER

**Specific problem:** The requirements supply average logical sizes—about 2 KB
for a profile and 500 bytes for account information—but no physical record
composition, serialization estimate, CDT overhead, p95/p99/maximum size, or
number of records per logical response.

**Affected access patterns:** AP-1 through AP-8, especially AP-2 and AP-8 if
multiple account payloads are consolidated.

**Consequence:** Storage I/O, network payload, primary-index efficiency, device
bandwidth, maximum-record-size exposure, and capacity cannot be calculated.
Aerospike reads and rewrites complete records on storage even when only selected
bins cross the network.

**Alternatives to evaluate:**

- Create a sizing worksheet for every candidate record boundary using p50,
  p95, p99, and worst-case element counts and payload sizes.
- Consolidate small, co-accessed data when bounded and not write-hot.
- Split large or independently accessed/hot data and accept a measured batch or
  fan-out cost.

### 5. Record growth — BLOCKER

**Specific problem:** There is no growth model for accounts per customer,
customer-account relationships, profile evolution, or recent-account history.
Only the average account count is known.

**Affected access patterns:** AP-2, AP-5, AP-6, and AP-8; AP-1 if related data is
eventually consolidated with the profile.

**Consequence:** A design may pass at average size but fail for high-cardinality
customers, future schema expansion, or unbounded history. Pagination would bound
a response, not the underlying record.

**Alternatives to evaluate:**

- A hard collection cap with deterministic trim/eviction behavior.
- Time- or count-bucketed records.
- Sharded relationship/history records with explicit overflow triggers.
- One record per independently accessed item when index cost and batch fan-out
  are justified by measurements.

### 6. CDT selection — HIGH

**Specific problem:** No decision exists between flat bins, list/map CDTs, and
multiple records. Ordering, uniqueness, lookup-by-account-ID, and partial-update
semantics are also unknown.

**Affected access patterns:** AP-2, AP-5, AP-6, and AP-8; potentially AP-1 and
AP-4 depending on the future profile shape.

**Consequence:** The model may require client-side read-modify-write, lose
atomicity, transfer unnecessary data, or choose a collection type that does not
match ordering and identity semantics.

**Alternatives to evaluate:**

- Flat bins for fixed fields read and written together.
- A bounded map when stable account identity and lookup/removal by account key
  dominate.
- A bounded ordered or unique list when positional/rank/time ordering is the
  primary semantic.
- Separate records when independent access, hotness, or growth makes an embedded
  collection unsuitable.

If a CDT is selected, updates should use supported server-side CDT operations
rather than an unprotected client read-modify-write cycle.

### 7. CDT growth bounds — BLOCKER

**Specific problem:** No CDT has been proposed, and no element cap, byte cap,
overflow threshold, trim rule, retention window, or p99 growth estimate exists
for either accounts or recent-account history.

**Affected access patterns:** AP-2, AP-5, AP-6, and AP-8.

**Consequence:** Any future list/map embedding could grow without bound, create
a hot and oversized record, increase migration/I/O cost, and eventually reject
writes at the record-size limit.

**Alternatives to evaluate:**

- Bounded server-side append/put plus trim behavior.
- Fixed-count or fixed-time recent-history retention.
- Overflow buckets or key partitioning.
- Separate item records when the domain requires unbounded history.

### 8. TTL behavior — BLOCKER

**Specific problem:** “Customer profile data has a 24-hour TTL” is not defined
as fixed or sliding, authoritative deletion or cache freshness, nor anchored to
creation, refresh, write, or read. It is unknown whether contact, status,
username resolution, relationships, and recent history share that lifetime.
NSUP/default-TTL/read-touch behavior is not specified.

**Affected access patterns:** AP-1, AP-3, AP-4, and AP-7 directly; AP-2, AP-5,
AP-6, and AP-8 if relationships/history share a profile boundary.

**Consequence:** Records may expire too early, have their TTL reset by ordinary
writes, survive longer than required, reject TTL writes when NSUP is disabled,
or make persistent accounts unreachable. Careless TTL reduction also has
cold-restart correctness implications.

**Alternatives to evaluate:**

- Fixed expiration from source refresh, with updates preserving void-time.
- Sliding expiration driven by an explicitly approved read-touch policy.
- Refresh-on-write semantics where every qualifying write intentionally rebases
  the horizon.
- Separate record lifetimes for expiring profile data and persistent account or
  relationship data.

Whichever requirement is selected must be aligned with namespace/set default
TTL, client TTL values, and NSUP. This review does not select one.

### 9. Hot-key and hot-record risks — BLOCKER

**Specific problem:** Aggregate throughput is known, but per-path distribution,
single-customer concurrency, skew, and recent-access write frequency are not.
There is no key design or record boundary to inspect for concentrated work.

**Affected access patterns:** AP-1 through AP-8, especially AP-4 through AP-6
and AP-8 because they mutate customer-scoped state.

**Consequence:** A high-traffic customer could serialize work on one record,
causing latency, timeouts, retries, or `KEY_BUSY`; a large frequently rewritten
record would compound the problem.

**Alternatives to evaluate:**

- Keep a bounded customer-scoped record if measured per-key concurrency is low.
- Separate independently hot mutable data from cold profile data.
- Partition/bucket a high-rate history or aggregate across keys.
- Combine multiple same-record changes into one atomic operation rather than
  repeated operations on the same key.

### 10. Secondary indexes — HIGH

**Specific problem:** No secondary index is proposed and no path has been shown
to require one. AP-7 is an inverse lookup, but username uniqueness and key
knowability are unresolved.

**Affected access patterns:** Primarily AP-7; any undisclosed administrative or
predicate search would also be affected.

**Consequence:** Reviewers cannot evaluate index selectivity, memory cost,
candidate-set size, or write amplification. Adding a high-cardinality username
index without comparing a deterministic lookup key could create unnecessary
query and index cost.

**Alternatives to evaluate:**

- Resolve unique username through a deterministic primary-key lookup record.
- Use a secondary index only for a confirmed query with sensible selectivity
  and an unknown key set.
- Confirm that no secondary index is required if all production paths resolve
  through known keys.

### 11. Expression indexes — MEDIUM

**Specific problem:** No computed or sparse predicate requiring an expression
index is documented, and the target Aerospike version/edition is unresolved.

**Affected access patterns:** None can currently be proven to need an expression
index; potential future status/filter paths are not defined.

**Consequence:** An expression index cannot be justified, version-checked, sized,
or costed. Introducing one speculatively would add index memory and write work
without a validated access path.

**Alternatives to evaluate:**

- Use no expression index when known-key access satisfies the path.
- Use a normal secondary index when the stored value itself is the required
  selective predicate.
- Evaluate a version-supported expression index only when a confirmed query
  requires a computed or sparse indexed value.

### 12. Query requirements — BLOCKER

**Specific problem:** The current requirements do not distinguish point lookups
from true unknown-key predicate queries. Username lookup is not sufficiently
defined, and no filter cardinalities or result bounds are supplied.

**Affected access patterns:** AP-7 directly; AP-2 and AP-8 if their keys cannot
be derived from the customer relationship design.

**Consequence:** The model could misuse query as a substitute for primary-key
design, return large candidate sets, or fail latency objectives at 5 million
reads/sec.

**Alternatives to evaluate:**

- Direct primary-key lookup when a unique lookup key can be derived.
- Known-key batch hydration after resolving a bounded list of IDs.
- Secondary-index query plus server-side filtering only for a genuine
  unknown-key predicate path with bounded/selective results.

### 13. Batch requirements — HIGH

**Specific problem:** It is unknown whether AP-2 and AP-8 return embedded data
or must hydrate multiple independently keyed account records. No batch size,
partial-failure behavior, duplicate-key handling, or latency budget exists.

**Affected access patterns:** AP-2 and AP-8; possibly bulk paths not yet listed.

**Consequence:** Read amplification and round trips cannot be estimated. A naive
serial loop could miss latency targets; an unbounded batch could create resource
spikes; ignoring per-key results could silently return incomplete data.

**Alternatives to evaluate:**

- Return bounded embedded account projections when co-access and update cost
  justify them.
- Resolve bounded known account keys and use a batch read, with one entry per
  key and explicit per-key result handling.
- Split or page large key sets into bounded batches.

### 14. Scan requirements — HIGH

**Specific problem:** No online or offline scan use case is stated, but the
clarification document also leaves administrative/bulk paths unresolved.

**Affected access patterns:** None of AP-1 through AP-8 should be assumed to
require a scan; missing administrative, reconciliation, export, or repair paths
may do so.

**Consequence:** A hidden online scan dependency could be operationally
expensive and incompatible with real-time latency. Conversely, declaring scans
unnecessary before discovering maintenance requirements would leave the model
and operational plan incomplete.

**Alternatives to evaluate:**

- Confirm explicitly that the real-time API has no scan path.
- Define bounded key-driven or query-driven operational work where possible.
- Isolate a justified offline scan/reconciliation workflow with separate SLOs
  and operational controls.

### 15. Denormalization — BLOCKER

**Specific problem:** No duplication or projection decisions exist for profile,
status, account summaries, username resolution, or recent-account results.

**Affected access patterns:** AP-1, AP-2, AP-3, AP-7, and AP-8; mutation paths
AP-4 through AP-6 must maintain any duplicated values.

**Consequence:** A normalized design could require application-side joins and
extra round trips; over-denormalization could multiply writes, create stale
copies, or enlarge hot records.

**Alternatives to evaluate:**

- Duplicate bounded response fields needed to satisfy a dominant path in one
  primary-key read.
- Store identifiers and use a bounded batch when freshness and write cost favor
  one authoritative copy.
- Maintain purpose-specific projections only with explicit ownership,
  propagation, consistency, and repair rules.

### 16. Relationship handling — BLOCKER

**Specific problem:** Customer-account cardinality, joint/delegated ownership,
reverse lookup needs, lifecycle, ordering, and add/remove atomicity are unknown.

**Affected access patterns:** AP-2, AP-5, and AP-6; AP-8 may reference the same
accounts and AP-1 may expose relationship-derived data.

**Consequence:** The model cannot choose relationship direction, consolidation,
or overflow behavior. Add/remove may leave one side stale, delete persistent
account data accidentally, or fail for high-cardinality customers.

**Alternatives to evaluate:**

- A bounded customer-owned relationship collection when ownership is one-way
  and cardinality is demonstrably bounded.
- Relationship buckets/partitions when one customer can have many accounts.
- Separate directional relationship records when reverse access is required.
- Deliberately duplicated relationship projections with defined atomicity,
  compensation, and repair behavior.

### 17. Consistency requirements — BLOCKER

**Specific problem:** No per-path stale-read tolerance, read-your-write rule,
ordering guarantee, durability acknowledgement, compare-and-swap requirement,
or multi-record atomicity requirement is confirmed.

**Affected access patterns:** AP-1 through AP-8, with correctness-sensitive
focus on AP-4 through AP-7.

**Consequence:** Namespace consistency mode and read/write semantics cannot be
selected. Username uniqueness, contact updates, and account linking could race
or expose partial state. It is also impossible to determine whether a proposed
multi-record operation would satisfy banking correctness.

**Alternatives to evaluate:**

- Record-local atomic operations for changes contained under one key.
- Generation-based conditional writes when client edits must reject concurrent
  changes.
- Explicit multi-record consistency/transaction requirements, checked against
  target-version limits, only where business atomicity crosses keys.
- Eventual consistency with repair/compensation only where the business allows
  temporary divergence.

### 18. Write amplification — BLOCKER

**Specific problem:** There is no record composition, update-rate breakdown,
TTL-touch policy, denormalization plan, or index plan from which to calculate
bytes rewritten or copies updated per business mutation.

**Affected access patterns:** AP-4, AP-5, AP-6, and the implicit recent-access
write behind AP-8; profile refresh and status writes are also missing paths.

**Consequence:** A small contact or recent-access change might rewrite a large
record, update several projections/indexes, generate replication traffic, and
consume device/defrag bandwidth at 500,000 writes/sec.

**Alternatives to evaluate:**

- Keep frequently updated data in a small bounded record separate from cold
  profile/account payloads.
- Consolidate low-rate changes when one atomic record operation and one read
  materially reduce overall work.
- Use supported server-side bin/CDT operations to avoid client round trips while
  still accounting for Aerospike's full-record storage rewrite.
- Minimize indexes and duplicated projections to those justified by confirmed
  paths.

### 19. Read amplification — BLOCKER

**Specific problem:** No path-to-record mapping exists, so the number of record
reads, device bytes, batch entries, queries, and response-assembly steps per API
call is unknown.

**Affected access patterns:** AP-1, AP-2, AP-3, AP-7, and AP-8.

**Consequence:** The design cannot be checked against 5 million reads/sec or
latency targets. Excessive normalization could require multiple round trips,
while over-consolidation could read large records for small projections.

**Alternatives to evaluate:**

- One primary-key read for dominant projections when bounded and not write-hot.
- Bounded parallel batch reads for known independently keyed records.
- Purpose-specific denormalized summaries to avoid repeated hydration where the
  maintenance cost is acceptable.
- Measure complete record I/O as well as returned network bytes for each option.

### 20. Failure modes — BLOCKER

**Specific problem:** The installed skill's seven schema detection tests require
a drafted schema. There are no sets, bins, records, CDTs, keys, indexes, or
resolved read paths to test. The clarification artifact does already identify
unbounded-growth inputs as missing, which correctly blocks design.

**Affected access patterns:** AP-1 through AP-8.

**Consequence:** The review cannot determine whether a future draft exhibits:

1. One set/record shape per domain noun.
2. Secondary indexes used as the primary access mechanism.
3. Client-side collection read-modify-write instead of CDT operations.
4. Bins that multiply with data.
5. Normalization that forces response-assembly reads.
6. Unbounded collection growth.
7. Excessive primary-index overhead from tiny independent records.

It also cannot validate TTL rejection/refresh mistakes, hot-key contention,
batch partial-result handling, lost updates, relationship divergence, or
read/write amplification.

**Alternatives to evaluate:**

- Keep the current clarification gate closed until the listed blocking inputs
  are answered or explicitly approved as assumptions.
- Draft one entity group only after clarification, then run all seven detection
  tests before its stakeholder checkpoint.
- Add quantitative TTL, sizing, amplification, hot-key, and access-path tests to
  the schema guide.
- Reject or explicitly document any exception rather than silently changing the
  submitted model.

## Consolidated findings

| Area | Status | Primary reason |
|---|---|---|
| Access-pattern coverage | BLOCKED | Paths are listed but not fully specified or mapped |
| Record boundaries | BLOCKED | No records are defined |
| Primary keys | BLOCKED | No key contract or username resolution path |
| Size and growth | BLOCKED | Only averages; no record composition or bounds |
| CDT choice and bounds | BLOCKED | No collection design or caps |
| TTL | BLOCKED | Meaning, refresh, scope, and NSUP alignment unresolved |
| Hot-key risk | BLOCKED | No per-key skew/concurrency or boundaries |
| Indexes and queries | BLOCKED | No justified unknown-key predicate path |
| Batch and scans | BLOCKED | Response assembly and operational paths unresolved |
| Denormalization/relationships | BLOCKED | Ownership, cardinality, and maintenance undefined |
| Consistency | BLOCKED | No per-path guarantees |
| Amplification | BLOCKED | Cannot count records or bytes per operation |
| Failure-mode review | BLOCKED | No draft schema exists to test |

## Review decision

The clarification document should remain unchanged as the current source of
requirements gaps. No redesign is appropriate yet. The next reviewable input is
a completed clarification disposition followed by a draft for the first entity
group, including its access-path mapping, record/key/bin/CDT proposal, sizing
worksheet, TTL semantics, consistency requirements, and assumptions log.

No model changes were made by this review.
