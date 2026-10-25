# Event ingestion prototype (assignment use)

**Status: AI-assisted prototype; not approved by the APP-05 team.** This is a small, reviewable example for the individual architecture assignment. It is not the team's selected stack, MQTT contract, or production implementation.

## Scope

`src/backend/event_ingestion_prototype.py` uses only the Python standard library and SQLite. It demonstrates:

- validation separated from persistence;
- a database uniqueness constraint on `event_id` for durable idempotency, with conflicting reuse surfaced as an error;
- bounded retries for SQLite lock/busy errors, with storage failure surfaced to the caller;
- a configurable retention cleanup whose default is 28 days.

The sample payload keys are illustrative: `event_id`, `device_id`, `building_id`, `measured_at`, `metric`, `value`, and `unit`. They must be reconciled with the contract the team approves. No MQTT client, broker, API, authentication, alert rule, or production deployment is included.

## Decision boundary and assumptions

- The code treats an event ID as globally unique. Reusing an ID with different event content raises `IdempotencyConflict`. Confirm both rules against the approved MQTT schema.
- The retention example deletes by `measured_at`. The team must decide whether policy is based on measurement time, receipt time, or another operational timestamp.
- The retry limit and backoff are demonstration defaults, not performance commitments.
- The consumer that calls this service must acknowledge an event only after `ingest` returns successfully. If `EventStoreUnavailable` is raised, it must follow the eventual broker/client policy. That adapter is outside this prototype.
- A local 291-thread ingestion burst was measured and failed the target: 26 accepted, 265 storage errors, p95 terminal latency 3.4999 seconds. This is not a sustained-user/API benchmark; the application/API p95 target remains unvalidated.

## Review evidence

The first AI-assisted baseline is preserved at commit `a7e263df6d74522b23b6a2cba295ac6bce03bd9d`. It deliberately demonstrates three review findings:

1. **Swallowed exception / inconsistent error outcome:** the broad `except Exception` returns `accepted` even after validation or storage fails. A caller could acknowledge and lose an event.
2. **Process-local idempotency:** a Python set is reset on restart and is not shared by concurrent workers, so it cannot enforce the boundary.
3. **Low cohesion:** one function validates, deduplicates, creates schema, persists data, logs, and decides the response.

The reviewed C1 implementation is at commit `7ccec19b4f10a2e19c21e178706005f268762678`. It separates validation, repository, and orchestration; uses a database primary key to prevent duplicate rows; retries only lock/busy contention a bounded number of times; and raises typed validation, idempotency, and storage errors on the ingest path. The purge path still leaks a raw SQLite error (F02). Identical redelivery is returned as duplicate; conflicting reuse of an event ID is surfaced for caller handling.

This baseline defect was deliberately included and labeled as an assignment review example. It must not be treated as a pre-existing team defect or used in a deployed path.

## Executed evidence and reproduction

The reproducible scripts and recorded results are now in the branch:
- [Evidence README and commands](../testing/ad022/README.md)
- [Original local results](../testing/ad022/verification_results.json)
- [T09 shared-mapping characterization](../testing/ad022/refactor_results.json)

On the recorded Windows 11 / Python 3.12.14 / SQLite 3.53.1 run, T01-T07 pass their scoped assertions. T08 is the earlier one-use-helper experiment; the final behavior-preserving design uses T09, which compares the same 11 API outcomes and persisted row before/after extracting the event mapping at both INSERT and duplicate comparison sites.

F01 reproduces expired data being accepted again after purge. F02 reproduces raw OperationalError on purge before initialization. These remain unresolved; passing the characterization checks is not application acceptance.

A single local burst used 291 threads/events: 26 accepted, 265 EventStoreUnavailable; p95 terminal latency 3.4999 seconds, p95 successful latency 3.5277 seconds. Results vary with the machine/scheduling. No production, MQTT, HTTP, sustained-user or dashboard benchmark has been completed.

The test scripts were also checked locally after being made runnable from repository paths, with --functional-only to avoid repeating load. This later check does not replace or rewrite the recorded burst.

## Remaining gates

- Approve the actual team schema, storage and ACK/requeue policy.
- Fix stale replay admission and consistent error mapping.
- Test MQTT crash-after-commit-before-ACK and alert side effects.
- Exercise 28-day recovery data, sustained agreed API workload, and production RTO/RPO targets.

