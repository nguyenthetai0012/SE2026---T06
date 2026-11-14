"""Seed registry từ file cấu hình có validate. Chạy lại không nhân bản; báo diff; không xóa lịch sử.

    cd src/backend && DATABASE_URL=... python -m app.seed [--file seed/registry.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import Settings
from .db import make_engine
from .models import Building, Device, Reading
from .params import ID_RE

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "seed" / "registry.json"


class SeedError(ValueError):
    pass


def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    buildings, devices = data.get("buildings"), data.get("devices")
    if not isinstance(buildings, list) or not isinstance(devices, list) or not buildings or not devices:
        raise SeedError("registry cần danh sách buildings và devices không rỗng")
    b_ids: set[str] = set()
    for b in buildings:
        if set(b) != {"building_id", "name"} or not ID_RE.match(str(b["building_id"])) or not str(b["name"]).strip():
            raise SeedError(f"building không hợp lệ: {b!r}")
        if b["building_id"] in b_ids:
            raise SeedError(f"trùng building_id: {b['building_id']}")
        b_ids.add(b["building_id"])
    d_ids: set[str] = set()
    for d in devices:
        want = {"device_id", "building_id", "name", "enabled", "period_seconds", "power_threshold_kw"}
        if set(d) != want:
            raise SeedError(f"device thiếu/thừa trường: {d!r}")
        if not ID_RE.match(str(d["device_id"])) or d["building_id"] not in b_ids or not str(d["name"]).strip():
            raise SeedError(f"device không hợp lệ: {d!r}")
        if not isinstance(d["enabled"], bool) or isinstance(d["period_seconds"], bool) or not isinstance(d["period_seconds"], int) or d["period_seconds"] <= 0:
            raise SeedError(f"enabled/period_seconds không hợp lệ: {d!r}")
        if isinstance(d["power_threshold_kw"], bool) or not isinstance(d["power_threshold_kw"], (int, float)) or d["power_threshold_kw"] < 0:
            raise SeedError(f"power_threshold_kw không hợp lệ: {d!r}")
        if d["device_id"] in d_ids:
            raise SeedError(f"trùng device_id: {d['device_id']}")
        d_ids.add(d["device_id"])
    return data


def apply_seed(db: Session, data: dict) -> dict[str, list[str]]:
    """Upsert idempotent. Trả diff {inserted, updated, unchanged}. Không đổi building của device đã có readings."""
    diff: dict[str, list[str]] = {"inserted": [], "updated": [], "unchanged": []}
    for b in data["buildings"]:
        row = db.get(Building, b["building_id"])
        if row is None:
            db.add(Building(**b)); diff["inserted"].append(f"building:{b['building_id']}")
        elif row.name != b["name"]:
            row.name = b["name"]; diff["updated"].append(f"building:{b['building_id']}")
        else:
            diff["unchanged"].append(f"building:{b['building_id']}")
    db.flush()
    for d in data["devices"]:
        row = db.get(Device, d["device_id"])
        threshold = Decimal(str(d["power_threshold_kw"]))
        if row is None:
            db.add(Device(**{**d, "power_threshold_kw": threshold})); diff["inserted"].append(f"device:{d['device_id']}")
            continue
        if row.building_id != d["building_id"]:
            n = db.scalar(select(func.count()).select_from(Reading).where(Reading.device_id == row.device_id))
            if n:
                raise SeedError(f"không đổi building của {row.device_id}: đã có {n} readings (cần dataset mới)")
        changed = [k for k in ("building_id", "name", "enabled", "period_seconds") if getattr(row, k) != d[k]]
        if row.power_threshold_kw != threshold:
            changed.append("power_threshold_kw")
        if changed:
            for k in changed:
                setattr(row, k, threshold if k == "power_threshold_kw" else d[k])
            diff["updated"].append(f"device:{d['device_id']}({','.join(changed)})")
        else:
            diff["unchanged"].append(f"device:{d['device_id']}")
    db.commit()
    return diff


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    args = ap.parse_args(argv)
    try:
        data = load_registry(args.file)
        settings = Settings.from_env()
        with Session(make_engine(settings.database_url, settings.statement_timeout_ms)) as db:
            diff = apply_seed(db, data)
    except SQLAlchemyError as exc:
        print(f"seed thất bại: lỗi cơ sở dữ liệu ({type(exc).__name__}); đã chạy `alembic upgrade head` chưa?", file=sys.stderr)
        return 1
    except (SeedError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"seed thất bại: {exc}", file=sys.stderr)
        return 1
    for k, items in diff.items():
        print(f"{k}: {', '.join(items) if items else '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
