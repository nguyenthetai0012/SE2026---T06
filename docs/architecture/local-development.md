# Local Development and QA Infrastructure

## 1. Scope and current status

This guide describes the local QA infrastructure currently available in this repository.

The current Docker Compose configuration provides:

- PostgreSQL 16 for local QA.

- Eclipse Mosquitto 2 for local MQTT testing.

- Disposable PostgreSQL and a Backend QA runner through an optional Compose overlay.

The current setup does not provide a complete application stack. The API, ingestion worker, migration, seed, frontend, and simulator services are not yet available as services in the current Compose configuration.

The proposed service names are documented in `docs/tasks/mvp-implementation.md`. Future implementation must remain aligned with that document.

## 2. Prerequisites

Install and make available:

- Docker Desktop with Docker Compose v2.

- Python 3.

- Git.

Run commands from the repository root.

## 3. Initialize local QA configuration

Create the local environment file:

```powershell

python3 tools/scripts/dev.py init

```

This creates `.env` with a randomly generated PostgreSQL password and the default MQTT port if the file does not already exist.

The script preserves an existing `.env` file. Do not commit `.env` or share its secret values.

## 4. Validate and start infrastructure

Validate the Compose configuration:

```powershell

python3 tools/scripts/dev.py config

```

Start PostgreSQL and Mosquitto:

```powershell

python3 tools/scripts/dev.py up

```

Check service status:

```powershell

python3 tools/scripts/dev.py status

```

The current Compose services are:

| Service | Purpose |

|---|---|

| `db` | PostgreSQL QA database |

| `mqtt` | Local Mosquitto MQTT broker |

PostgreSQL is not published to a host port by default. Containers communicate with it through `db:5432`.

The MQTT broker is published to `127.0.0.1` using `MQTT_PORT`, which defaults to `1883`.

## 5. Run infrastructure smoke checks

Run:

```powershell

python3 tools/scripts/dev.py smoke

```

The smoke check verifies:

- PostgreSQL responds to `SELECT 1`.

- Mosquitto supports a local MQTT publish/subscribe round trip.

A successful result only demonstrates infrastructure connectivity. It does not prove that the Backend, ingestion worker, simulator, API, or frontend works.

## 6. Stop local infrastructure

Run:

```powershell

python3 tools/scripts/dev.py down

```

This stops the Compose services while retaining their named volumes.

Do not use `docker compose down -v` unless intentionally deleting persistent local data.

## 7. Optional Backend QA workflow

The repository includes an optional Backend QA configuration:

- `infrastructure/docker/compose.backend-qa.yml`

- `infrastructure/docker/Dockerfile.backend-qa`

- `infrastructure/docker/run_backend_qa.py`

- `.github/workflows/qa.yml`

With Backend in the checkout, run from the repository root:

```sh
python tools/scripts/dev.py init
python tools/scripts/backend_qa.py
```

The runner requires Docker Compose, creates a disposable `app05_test` database and runs the real Backend migration, registry seed and API integration tests. The tests drop the test schema: never point them at a shared or production database. Reports go to `build/qa/`; they are local output and must not be committed. The QA workflow runs the same job on pull requests and main, uploads its reports, and supports manual dispatch. The separate frontend workflow tests the UI; neither smoke job is a full-system test.

A successful infrastructure smoke check is not a substitute for this Backend QA job.

## 8. MQTT security limitation

The current local Mosquitto configuration uses:

```conf

allow_anonymous true

```

This is a known limitation intended only for a trusted local demo environment.

The Compose host port is bound to `127.0.0.1`, but anonymous access does not provide authentication or topic-level authorization.

Do not expose this broker to an untrusted network or public deployment. Authentication, ACLs, and TLS must be designed and configured before remote exposure.

## 9. Current limitations and future integration

The proposed integration architecture in `docs/tasks/mvp-implementation.md` describes the intended services:

`db`, `mqtt`, `migrate`, `seed`, `api`, `worker`, `frontend`, and `simulator`.

Only `db` and `mqtt` are currently available in the main QA Compose file. The optional Backend QA overlay adds `db-test` and `backend-qa` for isolated Backend testing.

The remaining application services must be added when their implementations and startup commands are available. When these services are added, their Compose service names will remain consistent with the MVP implementation guide to avoid breaking the local development workflow and documentation.

Full integration, end-to-end, and load-test evidence must be recorded only after the corresponding application components are available and the tests have actually been executed.

## 10. Verification status
The following table distinguishes available infrastructure,
locally verified components, and integration steps that remain unverified.
| Component | Current status | Evidence / limitation |
|---|---|---|
| PostgreSQL QA | Verified | Local QA smoke check |
| MQTT broker | Verified | Local publish/subscribe smoke check |
| Backend local setup | Reported verified | Commands confirmed by Tài in PR #30; not verified through the current Compose setup |
| Backend Docker QA | Configured, pending verification | Optional QA workflow |
| Simulator | Not verified | Startup instructions and execution evidence pending |
| Frontend/Dashboard | Not verified | Startup instructions and execution evidence pending |
| Full E2E integration | Not verified | Complete Simulator-to-Dashboard flow has not been demonstrated |
Do not interpret infrastructure smoke-test success as evidence
of complete application integration.
Update this table only when corresponding commands have been
executed and their results have been recorded.
## 11. Related documentation

- [MVP system architecture](mvp-system.md)

- [MVP implementation guide](../tasks/mvp-implementation.md)

- [MVP baseline](../decisions/mvp-baseline.md)


## 12. Integration and bounded load plan (Issues #22 and #39)

Backend API setup and health checks are in [Backend README](../../src/backend/README.md); the Dashboard mock/API switch is in [Frontend README](../../src/frontend/README.md). Start a test-only database, migrate and seed, start the API and check `/api/v1/health/ready` before starting the UI. The optional Compose QA runner above checks the backend in an isolated database; it does not start the dashboard or ingestion worker.

The worker is under review in PR #41; Simulator #36 has not supplied an integration-ready revision. Their startup, shutdown and configuration instructions must be confirmed by Tài and An before this guide can claim a reproducible full-stack run. Sương must verify the browser against API data originating from MQTT. Record exact commits, versions, commands, non-secret configuration, observed IDs and results; do not reset any shared database. MQTT anonymous mode is only for a trusted local test.

| Scenario | Input and observation after MQTT, DB and API are available | Status |
| --- | --- | --- |
| Valid | Publish a unique registered device reading; verify ID, building, value and timestamps in DB and history API, then Dashboard. | Pending Simulator and joint E2E run |
| Invalid | Publish a malformed or mismatched reading; compare DB, alerts and device timestamps before/after, verify rejection. | Pending broker-to-API run |
| Duplicate | Republish identical message ID and body; assert exactly one reading and no duplicate alert or status change. | Pending broker-to-API run |
| Late | Publish an old event with unique ID; verify `is_late`, event/receive times and unchanged latest event watermark. | Pending broker-to-API run |
| Out of order | Send newer then older event for one device/metric; assert both persisted, correct flag and API event ordering. | Pending broker-to-API run |

### Bounded load preparation

An and Ngọc must agree an isolated test profile before running: registry, deterministic seed, explicit finite message count or duration, rate and maximum concurrency; start small and stop on errors. Save the generated message IDs and expected counts. After publisher completion, wait for the worker to drain with a bounded timeout; reconcile unique accepted IDs against database and API, accounting for deliberate duplicate and invalid inputs. Record sent, accepted, rejected, duplicates, pending and failures, throughput, ingest/API latency percentiles and resource usage, with environment, versions and commit SHAs. Mark the run inconclusive if pending messages or discrepancies remain. No throughput or latency SLA is established, and no load result is claimed here.


## Pipeline test on the integration branch

This branch combines the unmerged QA #35, worker #41 and Simulator #46 revisions for testing; it does not establish that those PRs have been merged. `python tools/scripts/dev.py init` followed by `python tools/scripts/backend_qa.py` runs the backend integration suite in a disposable PostgreSQL container. The QA container installs Mosquitto and requires its broker tests to run. The Simulator pipeline test sends normal, duplicate, invalid, late and out-of-order messages through the CLI, broker and worker, checks DB rows and flags and queries the Backend API application. The test uses fixed historical timestamps, so even the normal readings are late; it does not measure live latency or test the dashboard.

`TEST_DATABASE_URL` in the runner points only to its disposable `app05_test` database; the backend tests drop its public schema. Do not aim them at an existing or shared database. No local execution or CI result is implied by this instruction. The architecture says disabled devices are rejected, but worker #41 accepts readings for disabled devices; Simulator #46 sends only for enabled devices. Tài and An need to resolve that discrepancy before treating it as an agreed rule.
