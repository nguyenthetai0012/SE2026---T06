"""Helper cho test export (BT3 VT-023). Ghi trực tiếp bằng SQL để test không phụ thuộc code đang được kiểm.

Hợp đồng lưu trữ được kiểm ở đây: token chỉ lưu dạng SHA-256 hex, không lưu bản rõ.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "docs" / "testing" / "fixtures" / "mvp-normal.json"
REGISTRY = ROOT / "src" / "backend" / "seed" / "registry.json"

EXPORTS = "/api/v1/exports"
START, END = "2026-10-27T00:00:00Z", "2026-10-27T00:03:00Z"
CSV_HEADER = ["message_id", "device_id", "building_id", "metric", "event_time", "received_at",
              "interval_start", "value", "unit", "is_late", "is_out_of_order"]


def make_client(db, client_id: str, buildings: list[str], *, can_export: bool = True, enabled: bool = True) -> str:
    token = secrets.token_urlsafe(32)
    db.execute(text("INSERT INTO export_clients (client_id, name, token_sha256, can_export, enabled) "
                    "VALUES (:i, :n, :h, :c, :e)"),
               {"i": client_id, "n": f"test {client_id}", "h": hashlib.sha256(token.encode()).hexdigest(),
                "c": can_export, "e": enabled})
    for b in buildings:
        db.execute(text("INSERT INTO export_client_scopes (client_id, building_id) VALUES (:i, :b)"),
                   {"i": client_id, "b": b})
    db.commit()
    return token


def headers(token: str | None = None, key: str | None = None, raw_auth: str | None = None) -> dict:
    h = {}
    if raw_auth is not None:
        h["Authorization"] = raw_auth
    elif token is not None:
        h["Authorization"] = f"Bearer {token}"
    if key is not None:
        h["Idempotency-Key"] = key
    return h


def body(**override) -> dict:
    return {"building_id": "BLD-A", "metric": "power_kw", "start": START, "end": END} | override


def post(client, token=None, key="key-0000-0001", raw_auth=None, **override):
    return client.post(EXPORTS, json=body(**override), headers=headers(token, key, raw_auth))


def parse_csv(content: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(content.decode("utf-8"))))


def count_exports(db) -> int:
    return db.execute(text("SELECT count(*) FROM exports")).scalar()


def oracle_rows(building_id: str, metric: str, start: str, end: str) -> list[list[str]]:
    """Kết quả mong đợi tính độc lập từ fixture JSON + registry (không đọc từ DB/app)."""
    reg = {d["device_id"]: d["building_id"] for d in json.loads(REGISTRY.read_text("utf-8"))["devices"]}
    fx = json.loads(FIXTURE.read_text("utf-8"))
    out = []
    for m in fx["messages"]:
        p = m["payload"]
        if reg[p["device_id"]] == building_id and p["metric"] == metric and start <= p["event_time"] < end:
            out.append([p["message_id"], p["device_id"], building_id, metric, p["event_time"], m["received_at"],
                        p.get("interval_start") or "", str(p["value"]), "kW" if metric == "power_kw" else "kWh",
                        "false", "false"])
    return sorted(out, key=lambda r: (r[4], r[0]))
