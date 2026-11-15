#!/usr/bin/env python3
"""BT3 VT-023 — kiểm chứng tải: 200 tác vụ đồng thời trên API export, mục tiêu p95 <= 5.0 s.

Hai bước (server uvicorn thật + PostgreSQL thật, không mock):
    # 1) chuẩn bị DB riêng (tên phải chứa "load"): schema Alembic, seed, readings tổng hợp, 2 client
    DATABASE_URL=postgresql+psycopg://USER@localhost:5432/energy_load python tests/load/export_load.py prepare
    # 2) chạy server rồi bắn tải
    (cd src/backend && DATABASE_URL=... uvicorn app.main:create_app --factory --port 8800) &
    python tests/load/export_load.py run --base http://127.0.0.1:8800 --tokens /tmp/bt3_tokens.json

Kịch bản (bắt đầu cùng lúc bằng asyncio.Event):
  150 tác vụ "own":    POST (key riêng) -> POST lại cùng key (replay) -> GET tải CSV, kiểm SHA-256 = ETag
   40 tác vụ "shared": POST cùng MỘT key -> phải ra đúng 1 export (guard dưới tải)
   10 tác vụ "deny":   POST building ngoài scope (404) / GET export của client khác (404)
Dữ liệu: 3 thiết bị x 1440 reading power_kw/ngày (2026-11-01); mỗi export BLD-A = 2880 dòng (~330 KB).
Giới hạn kết luận: 1 máy, 1 tiến trình uvicorn, server và client chung máy; không phải môi trường triển khai.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "src" / "backend"
DAY = datetime(2026, 11, 1, tzinfo=timezone.utc)
BODY = {"building_id": "BLD-A", "metric": "power_kw", "start": "2026-11-01T00:00:00Z", "end": "2026-11-02T00:00:00Z"}
N_OWN, N_SHARED, N_DENY = 150, 40, 10


def prepare(tokens_path: Path) -> None:
    url = os.environ["DATABASE_URL"]
    sys.path.insert(0, str(BACKEND))
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session

    from app.export_clients import issue_client
    from app.seed import apply_seed, load_registry

    if "load" not in (make_url(url).database or ""):
        sys.exit("Từ chối: tên database phải chứa 'load' (sẽ DROP SCHEMA public).")
    eng = create_engine(url, connect_args={"options": "-c timezone=UTC"})
    with eng.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")
    with Session(eng) as db:
        apply_seed(db, load_registry(BACKEND / "seed" / "registry.json"))
        rows = []
        for dev in ("A-01", "A-02", "B-01"):
            for i in range(1440):
                ev = DAY + timedelta(minutes=i)
                rows.append({"m": f"00000000-0000-4000-8{dev[0]}{dev[-1]}-{i:012d}".lower().replace("a", "a"),
                             "d": dev, "ev": ev, "rc": ev + timedelta(seconds=1), "v": (i % 97) / 10})
        db.execute(text("INSERT INTO readings (message_id, device_id, metric, event_time, received_at, value, "
                        "is_late, is_out_of_order, period_seconds) VALUES (:m, :d, 'power_kw', :ev, :rc, :v, "
                        "false, false, 60)"), rows)
        db.commit()
        tokens = {"ops": issue_client(db, client_id="load-ops", name="load", buildings=["BLD-A"], can_export=True),
                  "other": issue_client(db, client_id="load-other", name="load2", buildings=["BLD-A", "BLD-B"],
                                        can_export=True)}
    tokens_path.write_text(json.dumps(tokens), "utf-8")
    os.chmod(tokens_path, 0o600)
    print(f"prepared: {len(rows)} readings, tokens -> {tokens_path}")


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, max(0, int(round(p / 100 * len(s) + 0.5)) - 1))]   # nearest-rank


async def run(base: str, tokens: dict, out: Path) -> int:
    import httpx

    lat: dict[str, list[float]] = {"create": [], "replay": [], "download": [], "shared": [], "deny": []}
    problems: list[str] = []
    go = asyncio.Event()
    limits = httpx.Limits(max_connections=N_OWN + N_SHARED + N_DENY, max_keepalive_connections=0)

    async def timed(kind, coro):
        t0 = time.perf_counter()
        r = await coro
        lat[kind].append(time.perf_counter() - t0)
        return r

    def h(tok, key=None):
        d = {"Authorization": f"Bearer {tok}"}
        if key:
            d["Idempotency-Key"] = key
        return d

    async with httpx.AsyncClient(base_url=base, timeout=60, limits=limits) as c:
        async def own(i):
            await go.wait()
            key = f"load-own-{i:04d}"
            r1 = await timed("create", c.post("/api/v1/exports", json=BODY, headers=h(tokens["ops"], key)))
            r2 = await timed("replay", c.post("/api/v1/exports", json=BODY, headers=h(tokens["ops"], key)))
            if (r1.status_code, r2.status_code) != (201, 200) or r1.json()["data"] != r2.json()["data"]:
                problems.append(f"own {i}: {r1.status_code}/{r2.status_code}")
                return None
            job = r1.json()["data"]
            r3 = await timed("download", c.get(job["download_url"], headers=h(tokens["ops"])))
            if r3.status_code != 200 or hashlib.sha256(r3.content).hexdigest() != job["content_sha256"] \
                    or r3.content.count(b"\r\n") != job["row_count"] + 1 or job["row_count"] != 2880:
                problems.append(f"own {i}: download mismatch")
            return job["export_id"]

        async def shared(i):
            await go.wait()
            r = await timed("shared", c.post("/api/v1/exports", json=BODY, headers=h(tokens["ops"], "load-shared-key")))
            if r.status_code not in (200, 201):
                problems.append(f"shared {i}: {r.status_code}")
                return None
            return r.status_code, r.json()["data"]["export_id"]

        async def deny(i):
            await go.wait()
            if i % 2:
                r = await timed("deny", c.post("/api/v1/exports", json={**BODY, "building_id": "BLD-B"},
                                               headers=h(tokens["ops"], f"load-deny-{i:04d}")))
            else:
                r = await timed("deny", c.get("/api/v1/exports/00000000-0000-4000-8000-000000000000",
                                              headers=h(tokens["other"])))
            if r.status_code != 404:
                problems.append(f"deny {i}: {r.status_code}")

        tasks = ([asyncio.create_task(own(i)) for i in range(N_OWN)]
                 + [asyncio.create_task(shared(i)) for i in range(N_SHARED)]
                 + [asyncio.create_task(deny(i)) for i in range(N_DENY)])
        await asyncio.sleep(0.5)
        t0 = time.perf_counter()
        go.set()
        res = await asyncio.gather(*tasks, return_exceptions=True)
        wall = time.perf_counter() - t0

    errors = [repr(r)[:120] for r in res if isinstance(r, BaseException)]
    shared_res = [r for r in res[N_OWN:N_OWN + N_SHARED] if isinstance(r, tuple)]
    shared_ids = {eid for _, eid in shared_res}
    shared_created = sum(1 for code, _ in shared_res if code == 201)
    if len(shared_ids) != 1 or shared_created != 1:
        problems.append(f"shared key: {len(shared_ids)} export_id, {shared_created} lần 201")
    all_lat = [x for v in lat.values() for x in v]
    report = {
        "when": datetime.now(timezone.utc).isoformat(timespec="seconds"), "base": base,
        "machine": {"python": platform.python_version(), "cpus": os.cpu_count(), "platform": platform.platform()},
        "concurrent_tasks": N_OWN + N_SHARED + N_DENY, "requests": len(all_lat), "wall_s": round(wall, 3),
        "p50_s": round(statistics.median(all_lat), 3), "p95_s": round(pct(all_lat, 95), 3),
        "max_s": round(max(all_lat), 3),
        "by_kind": {k: {"n": len(v), "p50_s": round(statistics.median(v), 3), "p95_s": round(pct(v, 95), 3),
                        "max_s": round(max(v), 3)} for k, v in lat.items() if v},
        "shared_key": {"responses": len(shared_res), "distinct_export_ids": len(shared_ids), "created_201": shared_created},
        "exceptions": errors, "problems": problems[:20],
        "target_p95_s": 5.0,
    }
    report["pass"] = report["p95_s"] <= 5.0 and not errors and not problems
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({k: report[k] for k in ("requests", "wall_s", "p50_s", "p95_s", "max_s", "shared_key", "pass")},
                     ensure_ascii=False))
    for k, v in report["by_kind"].items():
        print(f"  {k:9s} {v}")
    if errors or problems:
        print("  exceptions:", errors[:3], "problems:", problems[:5])
    return 0 if report["pass"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--tokens", type=Path, default=Path("/tmp/bt3_tokens.json"))
    r = sub.add_parser("run")
    r.add_argument("--base", default="http://127.0.0.1:8800")
    r.add_argument("--tokens", type=Path, default=Path("/tmp/bt3_tokens.json"))
    r.add_argument("--out", type=Path, default=Path("load-result.json"))
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare(a.tokens)
        return 0
    return asyncio.run(run(a.base, json.loads(a.tokens.read_text("utf-8")), a.out))


if __name__ == "__main__":
    raise SystemExit(main())
