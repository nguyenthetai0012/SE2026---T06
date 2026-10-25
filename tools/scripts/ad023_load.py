"""AD-023 concurrency test: 302 concurrent tasks against the Dashboard query
path while the rollup batch runs, fails on one partition and is recovered.

Each task is a thread with its own SQLite connection (WAL file DB) and a
Principal scoped to ONE building. Per task: 9 authorized requests
(overview / device history, 24h windows) + 1 attempt on another building,
which must be denied. Measures in-process service latency, not HTTP.

Usage: python tools/scripts/ad023_load.py [--out result.json] [--runs 3]
"""

import argparse
import json
import os
import platform
import random
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))

from ad023.app import build_app  # noqa: E402
from ad023.core.auth import AccessDenied, AuditLog, Principal, ScopeAuthPolicy  # noqa: E402
from ad023.dashboard.service import DashboardService  # noqa: E402
from ad023.infrastructure.rollup_store import SqliteRollupStore  # noqa: E402
from ad023.ingestion.energy_query import SqliteEnergyQuery  # noqa: E402
from ad023.reporting.batch import RollupBatch  # noqa: E402

TASKS = 302
REQUESTS_PER_TASK = 10           # 9 authorized + 1 cross-building attempt
TARGET_P95_MS = 1500
BUILDINGS, DEVICES, DAYS, STEP_MIN = 10, 10, 30, 15
START = datetime(2026, 9, 1, tzinfo=timezone.utc)
TODAY = date(2026, 10, 15)       # all seeded days are inside the 49-day retention


def percentile(values, p):
    values = sorted(values)
    k = (len(values) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def seed(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    app = build_app(conn)
    rows = []
    for b in range(BUILDINGS):
        for d in range(DEVICES):
            app.ingestion.register_device(f"BLD-{b:02d}-M{d:02d}", f"BLD-{b:02d}")
    for b in range(BUILDINGS):
        for d in range(DEVICES):
            device = f"BLD-{b:02d}-M{d:02d}"
            for i in range(DAYS * 24 * 60 // STEP_MIN):
                t = (START + timedelta(minutes=STEP_MIN * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
                rows.append((f"{device}-{i}", f"BLD-{b:02d}", device, "energy_kwh",
                             0.25 + (i % 7) * 0.01, t, t, "{}"))
    # Bulk load through the same table/constraints the ingestion module owns.
    conn.executemany("INSERT INTO sensor_readings (message_id, building_id, device_id, metric,"
                     " value, event_time, received_at, raw_payload) VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return len(rows)


def window(i):
    day = datetime(2026, 9, 2) + timedelta(days=i % (DAYS - 2))
    return day.strftime("%Y-%m-%dT00:00:00Z"), (day + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")


def worker(path, n, barrier, out, pool=None, think_ms=0):
    conn = sqlite3.connect(path, check_same_thread=False)
    svc = DashboardService(SqliteEnergyQuery(conn), ScopeAuthPolicy(), AuditLog())
    own, other = n % BUILDINGS, (n + 1) % BUILDINGS
    me = Principal(f"user-{n}", frozenset({f"BLD-{own:02d}"}))
    lat, denied, leaked, errors = [], 0, 0, 0
    rng = random.Random(n)  # reproducible think times per task
    barrier.wait()
    for r in range(REQUESTS_PER_TASK):
        if think_ms:  # user pause before each request, uniform 0..2*think_ms
            time.sleep(rng.uniform(0, 2 * think_ms) / 1000)
        t0 = time.perf_counter()  # includes time waiting for a pool slot
        if pool:
            pool.acquire()
        try:
            if r == REQUESTS_PER_TASK - 1:      # unauthorized attempt
                svc.get_building_overview(me, f"BLD-{other:02d}", *window(n + r))
                leaked += 1
            elif r % 2:
                svc.get_device_history(me, f"BLD-{own:02d}-M{(n + r) % DEVICES:02d}", *window(n + r))
            else:
                svc.get_building_overview(me, f"BLD-{own:02d}", *window(n + r))
        except AccessDenied:
            denied += 1
        except Exception:  # noqa: BLE001 - counted, reported
            errors += 1
        finally:
            if pool:
                pool.release()
        lat.append((time.perf_counter() - t0) * 1000)
    conn.close()
    out[n] = (lat, denied, leaked, errors)


def batch_during_load(path, barrier, out):
    conn = sqlite3.connect(path, timeout=30)
    energy, store = SqliteEnergyQuery(conn), SqliteRollupStore(conn)
    faulty = RollupBatch(energy, store, lambda: TODAY,
                         lambda b, kwh: kwh * 1000 if b == "BLD-03" else kwh)
    barrier.wait()
    t0 = time.perf_counter()
    days = [date(2026, 9, 1) + timedelta(days=d) for d in range(DAYS)]
    for day in days:
        faulty.execute(day)
    run_s = time.perf_counter() - t0
    fixed = RollupBatch(energy, store, lambda: TODAY)
    t1 = time.perf_counter()
    bad = {day.isoformat(): fixed.reconcile(day) for day in days}
    recomputed = sum(len(v) for v in bad.values())
    for day in days:
        fixed.recover(day, bad[day.isoformat()])
    remaining = sum(len(fixed.reconcile(day)) for day in days)
    out["batch"] = {"partitions": BUILDINGS * DAYS, "faulty_run_s": round(run_s, 3),
                    "bad_partitions_found": recomputed, "recovered_partitions": recomputed,
                    "recovery_s": round(time.perf_counter() - t1, 3),
                    "bad_after_recovery": remaining}
    conn.close()


def one_run(path, with_batch=True, pool_size=0, think_ms=0):
    barrier = threading.Barrier(TASKS + (1 if with_batch else 0))
    out = {}
    pool = threading.BoundedSemaphore(pool_size) if pool_size else None
    threads = [threading.Thread(target=worker, args=(path, n, barrier, out, pool, think_ms))
               for n in range(TASKS)]
    if with_batch:
        threads.append(threading.Thread(target=batch_during_load, args=(path, barrier, out)))
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    lat = [x for n in range(TASKS) for x in out[n][0]]
    return {
        "requests": len(lat),
        "p50_ms": round(statistics.median(lat), 2),
        "p95_ms": round(percentile(lat, 0.95), 2),
        "p99_ms": round(percentile(lat, 0.99), 2),
        "max_ms": round(max(lat), 2),
        "meets_p95_target": percentile(lat, 0.95) <= TARGET_P95_MS,
        "unauthorized_attempts": TASKS,
        "denied": sum(out[n][1] for n in range(TASKS)),
        "leaked": sum(out[n][2] for n in range(TASKS)),
        "errors": sum(out[n][3] for n in range(TASKS)),
        "wall_s": round(wall, 2),
        "batch": out.get("batch"),
        "with_batch": with_batch,
        "pool_size": pool_size or "unbounded (one per task)",
        "think_ms_mean": think_ms,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--no-batch", action="store_true")
    ap.add_argument("--pool", type=int, default=0, help="max concurrent queries (0 = unbounded)")
    ap.add_argument("--think-ms", type=int, default=0, help="mean pause before each request (0 = burst)")
    args = ap.parse_args()
    runs = []
    for _ in range(args.runs):
        with tempfile.TemporaryDirectory() as tmp:  # fresh DB: batch starts clean each run
            path = os.path.join(tmp, "ad023.db")
            readings = seed(path)
            runs.append(one_run(path, not args.no_batch, args.pool, args.think_ms))
    result = {
        "scenario": "302 concurrent tasks, 1 building scope each, 1 cross-building attempt each,"
                    " batch with one faulty building running concurrently then recovered",
        "args": vars(args),
        "target": {"concurrent_tasks": TASKS, "p95_ms_max": TARGET_P95_MS},
        "dataset": {"readings": readings, "buildings": BUILDINGS, "devices": BUILDINGS * DEVICES,
                    "days": DAYS},
        "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                        "cpus": os.cpu_count(), "store": "SQLite file, WAL, one connection per task",
                        "scope": "in-process service calls; no HTTP, MQTT or PostgreSQL"},
        "runs": runs,
    }
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
