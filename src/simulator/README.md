# APP-05 MQTT Simulator

Finite synthetic readings using the MVP MQTT contract. The baseline is accepted in part; Sương and Ngọc have not confirmed their parts. PR #41 worker is still under review. Disabled-device handling differs: the architecture says reject disabled devices, while PR #41 currently accepts them. This simulator selects enabled devices only; Tài and An should resolve that difference with the team.

## Setup

Run at the repository root with Python 3.12 and an isolated virtual environment:

```sh
python -m venv .venv
# activate .venv using your shell
python -m pip install -r src/simulator/requirements.txt
python -m src.simulator.simulator --mode normal --cycles 1 --seed 42 --dry-run
python -m unittest discover -s tests/integration/simulator -v
```

Start a trusted local MQTT 3.1.1 broker separately. Set `MQTT_HOST` and `MQTT_PORT` as needed; `MQTT_USERNAME` and `MQTT_PASSWORD` are optional environment variables and must not be committed. This local demo client does not configure TLS. Publish QoS 1 without retain; failure to obtain an acknowledgement within 10 seconds fails the run. A successful publish confirms broker acknowledgement, not worker ingestion.

```sh
python -m src.simulator.simulator --mode normal --cycles 2 --seed 42
python -m src.simulator.simulator --mode duplicate --cycles 1 --seed 42
python -m src.simulator.simulator --mode invalid --cycles 1 --seed 42
python -m src.simulator.simulator --mode late --cycles 1 --seed 42
python -m src.simulator.simulator --mode out-of-order --cycles 2 --seed 42
python -m src.simulator.simulator --mode offline --cycles 5 --seed 42
python -m src.simulator.simulator --mode load --cycles 10 --devices 3 --rate 5 --seed 42
```

`--cycles` is required and limits execution; non-load mode waits 60 seconds between batches so offline omits A-02 for three complete periods before resuming. Load rate limits publish attempts per second and `--devices` selects a prefix of enabled registry devices, up to registry size; it does not create unregistered devices. Stop manually with Ctrl+C if needed. Duplicate publishes the exact same topic and bytes twice. Invalid rotates missing value, string value, invalid timestamp, unknown device, wrong topic and oversized payload. Late subtracts one hour; out-of-order sends the second interval before the first. Test each scenario with an isolated dataset to avoid existing readings or overlapping intervals.

Default registry is `src/backend/seed/registry.json`; `--registry` accepts the same JSON shape. Only enabled devices with 60-second periods are currently supported. For reproducible payloads, retain both `--seed` and `--start` (UTC minute ending in Z), for example `--start 2026-10-27T00:00:00Z`; the last event must not be in the future. Without `--start`, the run chooses a past minute based on its length. Historical starts may legitimately be classified as late. IDs derive from seed, timestamp, device and metric; rerun the same dataset with the same arguments to preserve payloads and IDs. Use a new seed and non-overlapping times for new datasets. `logical_messages` and `publish_attempts` are separate; invalid messages count as logical generated messages, not accepted readings.

Broker, worker, database, API and Dashboard end-to-end verification is not claimed by the dry run or tests. Coordinate with Tài on PR #41, An on simulator scenarios/registry, and Ngọc on broker and load tests (#39).
