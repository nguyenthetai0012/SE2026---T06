"""Size rejection experiment: 80 tasks, 3 repeats, no database or network.

Inputs pad device_id to an exact JSON byte size; these are deliberately invalid
business identifiers. This measures the size gate including serialization, not
large valid events or MQTT transport. One immutable input is shared per burst.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import sys
from threading import Barrier
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "backend"))
from app.vt022_notification import process_reading


def make_event(size):
    event = {"message_id": "00000000-0000-4000-8000-000000000022", "device_id": "",
             "event_time": datetime(2026, 10, 27, tzinfo=timezone.utc), "value_kw": Decimal("12")}
    overhead = len(json.dumps(event, default=str, ensure_ascii=False).encode("utf-8"))
    event["device_id"] = "A" * (size - overhead)
    assert len(json.dumps(event, default=str, ensure_ascii=False).encode("utf-8")) == size
    return event


def burst(size, repeat):
    event = make_event(size)
    barrier = Barrier(80, timeout=30)

    def forbidden_sender(alert):
        raise AssertionError("sender must never run for oversized input")

    def invoke(_):
        barrier.wait()
        start = perf_counter()
        outcome = "unexpected_success"
        try:
            process_reading(None, event, forbidden_sender)
        except ValueError as exc:
            outcome = "size_rejected" if "size" in str(exc) else "other_value_error"
        except Exception as exc:
            outcome = "unexpected_" + type(exc).__name__
        return {"seconds": perf_counter() - start, "outcome": outcome}

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=80) as pool:
        results = list(pool.map(invoke, range(80)))
    wall = perf_counter() - started
    times = sorted(row["seconds"] for row in results)
    p95 = times[math.ceil(0.95 * len(times)) - 1]
    return {"bytes": size, "repeat": repeat, "tasks": 80,
            "rejected": sum(row["outcome"] == "size_rejected" for row in results),
            "p95_seconds": p95, "max_seconds": max(times), "wall_seconds": wall,
            "meets_2_5_seconds": p95 <= 2.5, "results": results}


if __name__ == "__main__":
    runs = [burst(size, repeat) for size in (4097, 65536, 1048576) for repeat in range(1, 4)]
    print(json.dumps({"scope": "in-process size gate; shared immutable input; no DB/network",
                      "p95_method": "nearest rank ceil(0.95*N); timing starts after barrier",
                      "runs": runs}, indent=2))
    raise SystemExit(0 if all(run["rejected"] == 80 and run["meets_2_5_seconds"] for run in runs) else 1)
