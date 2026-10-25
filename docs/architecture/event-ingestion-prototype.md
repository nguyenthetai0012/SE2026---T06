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
- The assignment targets (291 concurrent users/tasks and p95 <= 2.5 seconds) are not measured by this local SQLite prototype.

## Review evidence

The first AI-assisted baseline is preserved at commit `a7e263df6d74522b23b6a2cba295ac6bce03bd9d`. It deliberately demonstrates three review findings:

1. **Swallowed exception / inconsistent error outcome:** the broad `except Exception` returns `accepted` even after validation or storage fails. A caller could acknowledge and lose an event.
2. **Process-local idempotency:** a Python set is reset on restart and is not shared by concurrent workers, so it cannot enforce the boundary.
3. **Low cohesion:** one function validates, deduplicates, creates schema, persists data, logs, and decides the response.

The current refactored version is at commit `7ccec19b4f10a2e19c21e178706005f268762678`. It separates validation, repository, and orchestration; uses a database primary key to prevent duplicate rows; retries only lock/busy contention a bounded number of times; and raises typed validation, idempotency, and storage errors. Identical redelivery is returned as duplicate; conflicting reuse of an event ID is surfaced for caller handling.

This baseline defect was deliberately included and labeled as an assignment review example. It must not be treated as a pre-existing team defect or used in a deployed path.

## Planned regression checks (not run)

- Submit the same event ID twice with identical content, including after creating a new service/repository instance: one row remains and the second result is `duplicate`.
- Reuse an event ID with different content: the service raises `IdempotencyConflict` and leaves the original row unchanged.
- Submit malformed fields and a timestamp without an offset: validation fails and no row is written.
- Hold the SQLite database lock: retries are bounded; exhaustion raises `EventStoreUnavailable`, never `accepted`.
- Insert readings on both sides of the 28-day cutoff: only rows older than the selected cutoff are purged.
- Once the team fixes its target path, run a separate load scenario at 291 concurrent users/tasks and measure the agreed p95 path. This prototype has no evidence for that target yet.
