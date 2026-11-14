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



The GitHub Actions workflow exposes a manual `workflow_dispatch` input named `backend_ready`.



When Backend implementation is available in the checked-out revision, the workflow can run migration and API integration tests against a disposable PostgreSQL database and upload QA evidence as an artifact.



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



The remaining application services must be added when their implementations and startup commands are available.



Full integration, end-to-end, and load-test evidence must be recorded only after the corresponding application components are available and the tests have actually been executed.



## 10. Related documentation



- [MVP system architecture](mvp-system.md)

- [MVP implementation guide](../tasks/mvp-implementation.md)

- [MVP baseline](../decisions/mvp-baseline.md)
