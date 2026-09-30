# AGENTS.md

## Project purpose

This repository is used to develop and review Aerospike data models. Its primary
outputs are explicit, reviewable modeling decisions and schema documentation,
not application code.

Use the installed Aerospike skill at `.agents/skills/aerospike/` as the source
of truth for Aerospike modeling principles. Read its `SKILL.md` and the relevant
data-modeling references before creating or reviewing a model. Do not edit the
installed skill to change project policy.

## Scope and boundaries

- Keep schema design separate from client implementation.
- Do not generate client code, infrastructure, deployment configuration, or an
  application unless the task explicitly requests it after the model is agreed.
- Do not turn an entity list, ER diagram, or relational schema directly into
  Aerospike sets and records.
- Never invent Aerospike APIs, features, limits, defaults, or version support.
  Verify version-sensitive details against the installed skill and its linked
  official Aerospike sources.
- Do not silently fill requirement gaps. Ask a requirements-focused
  clarification question. If an input cannot be obtained, proceed only when the
  assumption is explicitly approved and record its reconsideration trigger.
- Work on one related entity group at a time and obtain a review checkpoint
  before moving to the next group.

## Required modeling workflow

### 1. Clarify before designing

The first artifact must be a written clarification document, not a schema. For
each input, record either its confirmed value and source or
`MISSING — question: ...`.

Before choosing namespaces, sets, keys, bins, or CDTs, identify:

- Domain entities, relationships, cardinality, ownership, and skew.
- Every read, create, update, and delete path.
- The lookup inputs and whether the primary key is known for each path.
- Frequency, concurrency, latency target, payload size, and result-size bounds.
- Expected and worst-case cardinality and growth, including a suitable future
  planning horizon.
- Retention, expiration, and TTL requirements.
- Consistency, atomicity, ordering, and durability requirements.
- Cleanup, cascade, and relationship-maintenance behavior.

Ask about missing requirements, not preferred Aerospike mechanisms. For example,
ask for expected fan-out and latency rather than asking whether a secondary
index should be used.

### 2. Build the access-pattern matrix

Document every read, write, update, and delete path before designing records.
For each path, capture at least:

- Actor or caller and business purpose.
- Lookup key or predicate and whether the key set is known.
- Expected frequency, concurrency, and latency objective.
- Data read or changed and expected payload size.
- Cardinality, fan-out, ordering, pagination, and skew.
- Required consistency and atomicity.
- Retention or TTL behavior.

Access patterns—not relational entities—must drive record granularity, key
design, denormalization, and index choices.

### 3. Plan entity groups

Partition related entities and access paths into groups that should be modeled
together. The plan is a routing and status artifact only; do not preselect sets,
indexes, or relationship patterns in it.

### 4. Design one entity group at a time

For each group:

1. Resolve group-specific clarification gaps.
2. Identify the record boundary explicitly and explain why it matches the
   access paths.
3. Identify namespace and set boundaries.
4. Define the primary-key strategy, including format, examples, cardinality,
   distribution, and skew risk.
5. Define bins, types, constraints, ownership, and update behavior.
6. Decide explicitly which data uses flat bins, CDTs, or separate records.
7. Model relationships and any deliberate denormalization required because
   Aerospike has no server-side joins.
8. Estimate record-size distribution, update frequency, growth, and overflow
   behavior.
9. Define TTL and expiration behavior and ensure it is compatible with the
   namespace design and NSUP requirements.
10. Define required consistency and atomicity semantics.
11. Map each access path to primary-key operations, bounded batch operations,
    CDT operations, expressions, secondary-index queries, or scans, with a
    rationale for any non-primary-key path.
12. Assess hot-key, hot-record, high-cardinality, and unbounded-growth risks.
13. Walk through create-and-read, multi-record mutation, and cleanup or cascade
    flows with a developer.
14. Pass a stakeholder checkpoint before starting the next entity group.

### 5. Validate across groups

After every group is reviewed:

- Confirm that every access pattern is supported.
- Derive the cross-group index and server-side filtering strategy.
- Verify version-gated features before relying on them.
- Run the failure-mode checks below.
- Record validation evidence and unresolved risks.

## Aerospike modeling principles

- Aerospike records are semi-structured, but the model is an application-level
  contract. Document namespace, set, key format, bin names, and bin types.
- A record is the unit of storage I/O. Reading selected bins reduces network
  transfer but does not make an oversized record cheap to read from storage.
- Every write rewrites the record. Evaluate record size together with update
  rate, contention, and storage I/O.
- Consolidate enough to avoid excessive tiny-record index overhead, but keep
  records bounded. Do not create a monolithic document or a hot key.
- Aerospike has no server-side joins. Denormalize deliberately when an access
  path otherwise needs extra record fetches solely to assemble its response.
- Prefer primary-key access. Use bounded batch operations when multiple known
  keys are required.
- Derive secondary indexes from validated query paths. Do not add an index for
  every field or use secondary-index queries as the default access strategy.
- Use expressions when justified for server-side filtering or computation, and
  verify feature/version support.
- Treat scans as explicit exceptional access paths with stated operational and
  latency implications, not as a substitute for key design.
- Keep list and map CDTs bounded. Define an element cap, growth forecast,
  overflow or sharding trigger, and cleanup policy.
- Prefer atomic server-side CDT operations and `operate`-style record operations
  over client-side read-modify-write when the required behavior is supported.
- Do not create bins whose count grows with the data. Bin names and types are
  part of the stable schema contract.
- Treat TTL as a model requirement. Document default and per-record behavior,
  update effects, retention expectations, and NSUP compatibility.
- Choose AP or strong-consistency semantics from application requirements, then
  align read, write, replica, commit, and atomicity expectations accordingly.
- Identify hot keys and hot records from concurrency and skew, especially for
  counters, shared aggregates, relationship collections, and repeated entries
  in batch work.

## Required design artifacts

Produce artifacts incrementally and write them to files rather than treating a
chat response as the model:

1. Clarification document with confirmed inputs, missing questions, sources,
   approved assumptions, and reconsideration triggers.
2. Entity and relationship map.
3. Access-pattern matrix.
4. Entity-group plan and review status.
5. Schema guide, built one reviewed group at a time.
6. Schema summary, generated from the completed schema guide.

The schema guide is authoritative and must contain:

- Namespace, set, key, bin, and CDT contracts.
- One example JSON record per set.
- Cardinality, skew, record-size, update-rate, and growth estimates.
- Relationship, consolidation, and denormalization decisions.
- TTL, consistency, atomicity, overflow, and hot-key plans.
- Index and expression rationale, expected selectivity, and resource impact.
- Alternatives rejected, assumptions made, and evidence that would reopen each
  decision.
- Access-path validation and failure-mode test results.

The schema summary is a condensed implementation contract containing one table
per set, key formats, bins and types, indexes, and growth or overflow triggers.
Never edit it independently. Update the schema guide and regenerate the summary.

## Mandatory review checks

Run these checks while designing and again before approval:

1. **Entity-list mapping:** Flag a model where sets map one-to-one to domain
   nouns without access-pattern justification.
2. **Index dependence:** Map every access path to its mechanism. Revisit the key
   strategy if secondary-index queries dominate routine access.
3. **CDT misuse:** Flag client-side read-modify-write of collection data when an
   atomic server-side CDT operation can perform it.
4. **Bins as columns:** Flag bin counts that grow with data or naming that does
   not form a stable contract.
5. **Accidental normalization:** Flag reads that fetch additional records only
   to assemble a response.
6. **Unbounded growth:** Require a design cap and overflow strategy for every
   collection. Pagination limits responses, not record growth.
7. **Tiny-record overhead:** Require an explicit sizing decision for small,
   independent records without solving the problem by creating one hot
   aggregate record.

Also verify that each design explicitly addresses:

- Record boundary and primary-key strategy.
- Bins versus CDTs versus separate records.
- Record-size distribution, write frequency, and future growth.
- TTL, expiration, consistency, and atomicity.
- Secondary indexes, expressions, queries, scans, and batch requirements.
- Denormalization and relationship maintenance.
- Hot-key, hot-record, skew, and high-cardinality risks.

## Completion criteria

A data model is not ready for client implementation until:

- Clarification gaps are resolved or explicitly approved as assumptions.
- Every entity group has passed its review checkpoint.
- Every access pattern maps to a documented operation path.
- The mandatory review checks pass or have documented, accepted exceptions.
- The schema guide is complete.
- The schema summary has been derived from the guide and is in sync.

When a check cannot be completed, state what is missing and stop at the
appropriate review gate rather than inventing an answer.
