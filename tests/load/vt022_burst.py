"""80 concurrent harness calls against a disposable, already-seeded test DB."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import sys
from threading import Barrier
from time import perf_counter
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))
from app.vt022_notification import process_reading

url = os.environ.get("TEST_DATABASE_URL", "")
if not url or "test" not in (make_url(url).database or ""):
    raise SystemExit("TEST_DATABASE_URL must name a disposable test database")
engine = create_engine(url, pool_size=20, max_overflow=0, pool_timeout=10)
barrier = Barrier(80, timeout=30)
start_time = datetime.now(timezone.utc)

def invoke(i, oversized=False):
    event = {"message_id": str(uuid4()), "device_id": "A" * 4100 if oversized else "A-01",
             "event_time": start_time + timedelta(microseconds=i), "value_kw": Decimal("12")}
    barrier.wait()
    start = perf_counter()
    try:
        outcome = process_reading(engine, event, lambda alert: None).notification_status
    except Exception as exc:
        outcome = type(exc).__name__
    return {"outcome": outcome, "seconds": perf_counter() - start}

with ThreadPoolExecutor(max_workers=80) as pool:
    results = list(pool.map(invoke, range(80)))
times = sorted(r["seconds"] for r in results)
counts = {k: sum(r["outcome"] == k for r in results) for k in sorted({r["outcome"] for r in results})}
with ThreadPoolExecutor(max_workers=80) as pool:
    oversized_results = list(pool.map(lambda i: invoke(i, oversized=True), range(80)))
oversized_times = sorted(r["seconds"] for r in oversized_results)
oversized_counts = {k: sum(r["outcome"] == k for r in oversized_results)
                    for k in sorted({r["outcome"] for r in oversized_results})}
print(json.dumps({"tasks": 80, "outcomes": counts, "p95_seconds_all": times[math.ceil(0.95 * len(times)) - 1],
                  "db_pool": 20, "sender": "in-process no-op", "results": results,
                  "oversized": {"outcomes": oversized_counts,
                                "p95_seconds_all": oversized_times[math.ceil(0.95 * len(times)) - 1],
                                "results": oversized_results}}, indent=2))
engine.dispose()
