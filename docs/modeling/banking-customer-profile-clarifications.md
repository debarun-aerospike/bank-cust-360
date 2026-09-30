# Banking Customer Profile Service: Clarification Document

## Status

- Phase: requirements clarification
- Clarification gate: open
- Schema design: not started
- Client implementation: out of scope
- Approved assumptions: none
- Source for confirmed inputs: user-provided requirements in the project
  conversation

No namespace, set, record boundary, key format, bin, CDT, index, expression,
query, scan, or batch design is selected in this document.

## Confirmed requirements

### Business operations

The service must support:

1. Fetch a customer profile by customer ID.
2. Fetch all accounts belonging to a customer.
3. Fetch a customer's current status.
4. Update customer contact information.
5. Add a new account to a customer.
6. Remove an account from a customer.
7. Fetch a customer by username.
8. Fetch recently accessed accounts for a customer.

### Scale and workload

- Customer population: 100 million.
- Average accounts per customer: 3.
- Approximate customer-profile size: 2 KB.
- Approximate account-information size: 500 bytes.
- Aggregate read rate: 5 million reads per second.
- Aggregate write rate: 500,000 writes per second.
- Most reads use customer ID.

### Retention

- Customer profile data has a 24-hour TTL.
- Account data is persistent.

## Domain vocabulary requiring confirmation

These are business concepts named or implied by the requirements. They are not
proposed Aerospike records or sets.

- Customer
- Customer profile
- Customer status
- Customer contact information
- Account
- Customer-to-account relationship
- Username-to-customer identity relationship
- Account-access event or recent-account history

The statement that accounts “belong to” a customer confirms a relationship but
does not establish its ownership cardinality, lifecycle, or whether joint/shared
accounts exist.

## Initial access-pattern inventory

This table records only what is known. `MISSING` entries must be clarified
before record design.

| ID | Operation | Supplied lookup input | Result or mutation | Missing inputs |
|---|---|---|---|---|
| AP-1 | Fetch customer profile | Customer ID | Customer profile | Exact fields, response composition, frequency, latency, consistency, missing/expired behavior |
| AP-2 | Fetch all customer accounts | Customer ID | All associated accounts | Cardinality distribution, ordering, filtering, pagination, payload bound, latency, consistency |
| AP-3 | Fetch current customer status | Customer ID | Current status | Status definition, source, update path, freshness, latency, consistency |
| AP-4 | Update contact information | Customer ID is implied but not confirmed | Contact-field mutation | Lookup input, fields, partial/full semantics, concurrency, validation, idempotency, latency, consistency |
| AP-5 | Add account to customer | Customer and account identifiers are implied | Relationship/account mutation | Ownership, create-vs-link semantics, atomicity, idempotency, validation, failure behavior |
| AP-6 | Remove account from customer | Customer and account identifiers are implied | Relationship/account mutation | Unlink-vs-delete semantics, atomicity, retention, idempotency, failure behavior |
| AP-7 | Fetch customer by username | Username | Customer result | Uniqueness scope, normalization, returned payload, rename/reuse behavior, latency, consistency |
| AP-8 | Fetch recently accessed accounts | Customer ID | Ordered recent-account result | Meaning of access, writer, window/cap, deduplication, ordering, payload, update rate, persistence, consistency |

## Missing requirements and clarification questions

### A. Identity, ownership, and relationships

1. `MISSING — question:` What are the format, maximum length, source, and
   immutability rules for customer IDs?
2. `MISSING — question:` What are the format, maximum length, source, and
   uniqueness scope of account IDs?
3. `MISSING — question:` Can one account belong to more than one customer, as
   with a joint or delegated account? If yes, what are the average, p99, and
   maximum owners per account?
4. `MISSING — question:` What are the expected p95, p99, and maximum account
   counts per customer now and at the chosen planning horizon? The average of
   three does not bound skew or record growth.
5. `MISSING — question:` Does “all accounts” include closed, suspended, hidden,
   delegated, or otherwise inactive accounts?
6. `MISSING — question:` Is adding an account creating account data, linking an
   existing account, or potentially either operation?
7. `MISSING — question:` Is removing an account only removing the relationship,
   closing the account, or deleting account data?
8. `MISSING — question:` What should happen to relationships and lookup paths
   when a customer is closed or deleted?

### B. Profile, status, contact, and account payloads

9. `MISSING — question:` What exact fields and data types make up the customer
   profile, and which fields are optional or sensitive?
10. `MISSING — question:` Is 2 KB an average serialized size? What are the p95,
    p99, and maximum profile sizes, including expected future growth?
11. `MISSING — question:` Is status part of the profile response, independently
    fetched data, or both? What are its allowed values and transition rules?
12. `MISSING — question:` What system produces status changes, how frequently
    can status change, and what is the maximum acceptable age of a status read?
13. `MISSING — question:` Which contact fields can be changed, and is an update
    a partial patch or complete replacement of contact information?
14. `MISSING — question:` What validation, verification, or workflow state must
    accompany changes to email addresses, phone numbers, or postal addresses?
15. `MISSING — question:` What exact fields and types make up the approximately
    500-byte account information, and what are its p95, p99, and maximum sizes?
16. `MISSING — question:` Does AP-2 return complete account information or only
    account summaries/identifiers?

### C. Read and mutation semantics

17. `MISSING — question:` Does AP-1 return only profile fields, or must it also
    include status, accounts, or recent-account data in one response?
18. `MISSING — question:` For AP-2, what ordering and filters are required, and
    must the result be paginated? If paginated, what is the maximum page size?
19. `MISSING — question:` What must AP-7 return: customer ID only, the full
    profile, status, or another defined projection?
20. `MISSING — question:` Must contact updates detect concurrent changes and
    reject lost updates? What conflict behavior is required?
21. `MISSING — question:` What idempotency guarantees and retry behavior are
    required for contact updates and account add/remove operations?
22. `MISSING — question:` When an account is added or removed, which observations
    must become visible atomically to readers?
23. `MISSING — question:` What validation must occur before an account may be
    linked or unlinked, and what is the required result if only part of the
    operation succeeds?
24. `MISSING — question:` Are bulk customer/account reads or bulk mutations,
    administrative searches, or other access paths required beyond AP-1 through
    AP-8?

### D. Username behavior

25. `MISSING — question:` Is username globally unique, unique within a tenant or
    region, or allowed to identify multiple customers?
26. `MISSING — question:` Are username comparisons case-sensitive, and what
    normalization rules apply to whitespace and Unicode?
27. `MISSING — question:` Can usernames change? If so, must old usernames
    redirect, stop resolving immediately, or remain reserved?
28. `MISSING — question:` Can a username ever be reused by another customer?
29. `MISSING — question:` What consistency is required between a username
    create/change and lookup—must uniqueness and lookup visibility be immediate?

### E. Recently accessed accounts

30. `MISSING — question:` What event counts as an account access, and which
    component records that event?
31. `MISSING — question:` Should repeated access to the same account appear once
    at its latest position or multiple times as separate events?
32. `MISSING — question:` Is “recent” defined by a fixed item count, a time
    window, or both? What are the maximum item count and retention period?
33. `MISSING — question:` What ordering and tie-breaking rules are required?
34. `MISSING — question:` Does AP-8 return account IDs, summaries, or complete
    account information?
35. `MISSING — question:` What are the expected and peak recent-access update
    rates per customer and globally?
36. `MISSING — question:` Must recent-account history survive profile expiry,
    customer inactivity, restart, or regional failover?
37. `MISSING — question:` What freshness, consistency, and read-your-write
    behavior are required for recent-account results?

### F. TTL and expiration semantics

38. `MISSING — question:` What business requirement does the 24-hour profile TTL
    represent: authoritative deletion, cache freshness, privacy retention, or
    another rule?
39. `MISSING — question:` From which event is the 24-hour period measured:
    profile creation, source refresh, write/update, or last read?
40. `MISSING — question:` Should reads refresh the TTL? Should contact or status
    updates reset it?
41. `MISSING — question:` When a profile expires, what is the required behavior
    for AP-1, AP-3, AP-4, and AP-7? Is there an authoritative source from which
    the profile is reloaded, and what is the miss-path latency objective?
42. `MISSING — question:` Do contact information and status share the profile's
    24-hour lifetime, or do they have different retention requirements?
43. `MISSING — question:` Must the customer-to-account association remain
    available when the profile expires so persistent account data is still
    reachable?
44. `MISSING — question:` How soon after the 24-hour deadline must expired data
    become unreadable or be physically removed?
45. `MISSING — question:` Can any update intentionally shorten an existing
    profile lifetime, and what should happen if it does?

### G. Consistency, atomicity, and durability

46. `MISSING — question:` For each AP-1 through AP-8, what stale-read tolerance,
    read-your-write requirement, and ordering guarantee applies?
47. `MISSING — question:` Which operations require strong consistency rather
    than availability during a partition or failover?
48. `MISSING — question:` What durability acknowledgement is required before a
    contact, status, account-link, or recent-access write may be reported as
    successful?
49. `MISSING — question:` Must account add/remove be atomic with any account
    record changes or reverse customer relationship, especially for shared
    accounts?
50. `MISSING — question:` Are conditional updates required using an expected
    version, timestamp, or other concurrency token?
51. `MISSING — question:` Will the service operate in one region or multiple
    regions? If multiple, which region may accept writes and what cross-region
    staleness or conflict behavior is acceptable?

### H. Workload distribution, SLOs, and skew

52. `MISSING — question:` Are 5 million reads/sec and 500,000 writes/sec peak or
    sustained rates, and what burst duration must be supported?
53. `MISSING — question:` What percentage and rate belong to each AP-1 through
    AP-8, including recent-access writes and status updates not listed as an
    explicit mutation path?
54. `MISSING — question:` What are the p50, p95, p99, and maximum latency
    objectives for each path?
55. `MISSING — question:` What availability and error-rate objectives apply to
    reads and writes?
56. `MISSING — question:` How skewed is traffic across customers and accounts?
    What are the peak read/write rates and concurrent operations for a single
    customer or account?
57. `MISSING — question:` What customer and account growth is expected over the
    planning horizon?
58. `MISSING — question:` What fraction of customers are active within a
    24-hour period, and how often are expired profiles rehydrated?

### I. Deletion, audit, security, and compliance

59. `MISSING — question:` What customer-deletion, account-closure, and data
    retention rules apply, including legal holds and required purge deadlines?
60. `MISSING — question:` Must historical profile, contact, status, relationship,
    or recent-access changes be retained for audit? If yes, where is that audit
    history owned and how is it accessed?
61. `MISSING — question:` Which fields are regulated or sensitive, and what
    encryption, masking, access-separation, or residency requirements affect
    their storage or duplication?
62. `MISSING — question:` Are account access and username lookup subject to
    authorization rules that change which data may be returned?

### J. Aerospike operating constraints

63. `MISSING — question:` What Aerospike Database version and edition will the
    service target? This is required before relying on version- or
    edition-gated capabilities.
64. `MISSING — question:` Is Aerospike the authoritative store for profiles,
    accounts, and relationships, or is it serving data mastered elsewhere?
65. `MISSING — question:` What storage architecture and namespace-level
    retention/consistency constraints already exist, if any?
66. `MISSING — question:` Are there pre-existing namespace, set, key-format, or
    compatibility constraints that this model must preserve?

## Blocking requirements for the next phase

Record design must not begin until, at minimum, the following are confirmed or
explicitly approved as assumptions with reconsideration triggers:

- Exact response and mutation semantics for AP-1 through AP-8.
- Account ownership cardinality and p99/maximum accounts per customer.
- Profile, account, status, contact, and recent-account payload definitions and
  size bounds.
- Username uniqueness, normalization, rename, and reuse rules.
- Recent-account definition, bound, retention, ordering, and write rate.
- The meaning and refresh/expiry behavior of the 24-hour profile TTL.
- Behavior of persistent accounts and relationships after profile expiry.
- Per-path consistency, atomicity, durability, and latency requirements.
- Workload breakdown, traffic skew, and single-key concurrency.
- Delete, audit, and regulatory-retention behavior.
- Target Aerospike version/edition and whether Aerospike is authoritative.

## Assumptions log

No assumptions have been made or approved. Every unresolved input remains
marked `MISSING` above.

## Next checkpoint

The next step is to answer or explicitly disposition the blocking questions.
Only then should the domain be partitioned into entity groups and the first
group-specific clarification pass begin. Schema design remains paused.
