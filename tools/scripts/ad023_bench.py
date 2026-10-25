"""AD-023 micro-benchmark of the Dashboard query path (in-process, SQLite).

Measures DashboardService latency only. It is NOT an HTTP, MQTT, PostgreSQL
or multi-user benchmark; numbers depend on the machine.

Usage (from repo root):
    python tools/scripts/ad023_bench.py [--src src/backend] [--out result.json]
Works on both the C1 API (no principal) and the C4 API (principal first).
"""

import argparse
import inspect
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone

BUILDINGS, DEVICES_PER_BUILDING, DAYS, STEP_MIN = 10, 10, 30, 15
CALLS, REPEATS = 500, 3


def percentile(values, p):
    values = sorted(values)
    k = (len(values) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def seed(app):
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    n = 0
    for b in range(BUILDINGS):
        building = f"BLD-{b:02d}"
        for d in range(DEVICES_PER_BUILDING):
            device = f"{building}-M{d:02d}"
            app.ingestion.register_device(device, building)
            for i in range(DAYS * 24 * 60 // STEP_MIN):
                t = (start + timedelta(minutes=STEP_MIN * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
                app.ingestion.clock = lambda t=t: t
                app.ingestion.ingest({"schema_version": "1.0", "message_id": f"{device}-{i}",
                                      "building_id": building, "device_id": device,
                                      "event_time": t, "metric": "energy_kwh",
                                      "value": 0.25 + (i % 7) * 0.01})
                n += 1
    app.conn.commit()
    return n


def measure(call):
    samples = []
    for i in range(CALLS):
        t0 = time.perf_counter()
        call(i)
        samples.append((time.perf_counter() - t0) * 1000)
    return {"p50_ms": round(statistics.median(samples), 3),
            "p95_ms": round(percentile(samples, 0.95), 3),
            "max_ms": round(max(samples), 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="src/backend")
    parser.add_argument("--out")
    parser.add_argument("--label", default="")
    args = parser.parse_args()
    sys.path.insert(0, args.src)
    from ad023.app import build_app

    app = build_app()
    t0 = time.perf_counter()
    rows = seed(app)
    seed_s = time.perf_counter() - t0

    svc = app.dashboard
    needs_principal = "principal" in inspect.signature(svc.get_building_overview).parameters
    args_prefix = ()
    if needs_principal:
        from ad023.core.auth import Principal
        args_prefix = (Principal("bench", frozenset(f"BLD-{b:02d}" for b in range(BUILDINGS))),)

    def window(i):
        day = datetime(2026, 9, 2) + timedelta(days=i % (DAYS - 2))
        return day.strftime("%Y-%m-%dT00:00:00Z"), (day + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    runs = []
    for _ in range(REPEATS):
        runs.append({
            "overview_24h": measure(lambda i: svc.get_building_overview(
                *args_prefix, f"BLD-{i % BUILDINGS:02d}", *window(i))),
            "device_history_24h": measure(lambda i: svc.get_device_history(
                *args_prefix, f"BLD-{i % BUILDINGS:02d}-M{i % DEVICES_PER_BUILDING:02d}", *window(i))),
        })

    result = {
        "label": args.label,
        "api": "C4 (principal)" if needs_principal else "C1 (no principal)",
        "dataset": {"buildings": BUILDINGS, "devices": BUILDINGS * DEVICES_PER_BUILDING,
                    "days": DAYS, "step_minutes": STEP_MIN, "readings": rows},
        "calls_per_operation": CALLS, "repeats": REPEATS,
        "seed_seconds": round(seed_s, 2),
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        "sqlite": __import__("sqlite3").sqlite_version, "store": "SQLite :memory:"},
        "runs": runs,
    }
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
