"""Truy vấn đọc. Quy tắc tính nằm ở đây, Frontend không tự tính (docs/contracts/mvp-mqtt.md, mvp-api.md)."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.orm import Session

from . import pagination
from .config import OFFLINE_MULTIPLIER
from .errors import filter_mismatch, not_found
from .models import Alert, Building, Device, Reading
from .params import UNIT


def device_status(enabled: bool, last_seen: datetime | None, period: int, now: datetime) -> str:
    if not enabled:
        return "disabled"
    if last_seen is None:
        return "unknown"
    return "offline" if now - last_seen >= timedelta(seconds=OFFLINE_MULTIPLIER * period) else "online"


def is_stale(latest_event_time: datetime | None, period: int, now: datetime) -> bool:
    # Cùng biên với offline: >= 3 * period.
    return latest_event_time is None or now - latest_event_time >= timedelta(seconds=OFFLINE_MULTIPLIER * period)


def _require_building(db: Session, building_id: str) -> None:
    if db.get(Building, building_id) is None:
        raise not_found(f"không có building_id={building_id}")


def _require_device(db: Session, device_id: str) -> Device:
    dev = db.get(Device, device_id)
    if dev is None:
        raise not_found(f"không có device_id={device_id}")
    return dev


def _td_seconds(td: timedelta) -> Decimal:
    return Decimal(td.days * 86400 + td.seconds) + Decimal(td.microseconds) / Decimal(1_000_000)


def building_summary(db: Session, start: datetime, end: datetime, building_id: str | None, now: datetime) -> list[dict]:
    if building_id is not None:
        _require_building(db, building_id)
    # Chỉ device đang enabled và chỉ interval nằm trọn trong [start, end] (không chia tỷ lệ interval biên).
    join_r = and_(
        Reading.device_id == Device.device_id, Reading.metric == "energy_kwh",
        Reading.interval_start >= start, Reading.event_time <= end,
    )
    stmt = (
        select(
            Building.building_id, Building.name,
            func.count(func.distinct(Device.device_id)).label("n_enabled"),
            func.count(Reading.message_id).label("cnt"),
            func.sum(Reading.value).label("total"),
            func.sum(func.extract("epoch", Reading.event_time - Reading.interval_start)).label("secs"),
        )
        .select_from(Building)
        .outerjoin(Device, and_(Device.building_id == Building.building_id, Device.enabled.is_(True)))
        .outerjoin(Reading, join_r)
        .group_by(Building.building_id, Building.name)
        .order_by(Building.building_id)
    )
    if building_id is not None:
        stmt = stmt.where(Building.building_id == building_id)
    rows = db.execute(stmt).all()

    stale_by_building: dict[str, bool] = {}
    for b_id, latest, period in db.execute(
        select(Device.building_id, Device.latest_event_time, Device.period_seconds).where(Device.enabled.is_(True))
    ):
        stale_by_building[b_id] = stale_by_building.get(b_id, False) or is_stale(latest, period, now)

    span = _td_seconds(end - start)
    out = []
    for r in rows:
        cnt = int(r.cnt)
        secs = Decimal(r.secs) if r.secs is not None else Decimal(0)
        denominator = span * int(r.n_enabled)
        if r.n_enabled == 0 or cnt == 0:
            ratio, coverage = Decimal(0), "none"
        else:
            ratio = secs / denominator
            coverage = "complete" if secs == denominator else "partial"
        out.append({
            "building_id": r.building_id, "name": r.name,
            # null (không có interval) khác 0 kWh đã đo.
            "energy_kwh": float(r.total) if cnt > 0 and r.total is not None else None,
            "unit": "kWh", "start": start, "end": end,
            "included_interval_count": cnt, "coverage": coverage, "coverage_ratio": float(ratio),
            # Không có enabled device nào -> không có dữ liệu để coi là stale.
            "data_stale": stale_by_building.get(r.building_id, False),
        })
    return out


def list_devices(db: Session, building_id: str | None, limit: int, cursor: str | None, now: datetime) -> tuple[list[dict], str | None]:
    if building_id is not None:
        _require_building(db, building_id)
    sig = pagination.signature("devices", building_id=building_id, limit=limit)
    stmt = select(Device).order_by(Device.device_id).limit(limit + 1)
    if building_id is not None:
        stmt = stmt.where(Device.building_id == building_id)
    if cursor is not None:
        (last_id,) = pagination.decode(cursor, sig, 1)
        stmt = stmt.where(Device.device_id > last_id)
    rows = list(db.scalars(stmt))
    page, more = rows[:limit], len(rows) > limit
    data = [{
        "device_id": d.device_id, "building_id": d.building_id, "name": d.name, "enabled": d.enabled,
        "status": device_status(d.enabled, d.last_seen, d.period_seconds, now),
        "last_seen": d.last_seen, "latest_event_time": d.latest_event_time,
        "data_stale": is_stale(d.latest_event_time, d.period_seconds, now), "period_seconds": d.period_seconds,
    } for d in page]
    return data, (pagination.encode(sig, [page[-1].device_id]) if more else None)


def device_history(db: Session, device_id: str, metric: str, start: datetime, end: datetime, limit: int, cursor: str | None) -> tuple[list[dict], str | None]:
    dev = _require_device(db, device_id)
    sig = pagination.signature("history", device_id=device_id, metric=metric, start=start.isoformat(), end=end.isoformat(), limit=limit)
    # Lịch sử dùng [start, end) theo event_time (khác ngữ nghĩa với summary).
    stmt = (
        select(Reading)
        .where(Reading.device_id == device_id, Reading.metric == metric, Reading.event_time >= start, Reading.event_time < end)
        .order_by(Reading.event_time, Reading.message_id)
        .limit(limit + 1)
    )
    if cursor is not None:
        ev, mid = pagination.decode(cursor, sig, 2)
        stmt = stmt.where(tuple_(Reading.event_time, Reading.message_id) > tuple_(pagination.parse_dt(ev), mid))
    rows = list(db.scalars(stmt))
    page, more = rows[:limit], len(rows) > limit
    data = [{
        "message_id": r.message_id, "device_id": r.device_id, "building_id": dev.building_id, "metric": r.metric,
        "event_time": r.event_time, "received_at": r.received_at, "interval_start": r.interval_start,
        "value": float(r.value), "unit": UNIT[r.metric], "is_late": r.is_late, "is_out_of_order": r.is_out_of_order,
    } for r in page]
    nxt = pagination.encode(sig, [page[-1].event_time.isoformat(), page[-1].message_id]) if more else None
    return data, nxt


def list_alerts(db: Session, building_id: str | None, device_id: str | None, limit: int, cursor: str | None) -> tuple[list[dict], str | None]:
    if building_id is not None:
        _require_building(db, building_id)
    if device_id is not None:
        dev = _require_device(db, device_id)
        if building_id is not None and dev.building_id != building_id:
            raise filter_mismatch("device_id không thuộc building_id đã chọn")
    sig = pagination.signature("alerts", building_id=building_id, device_id=device_id, limit=limit)
    stmt = (
        select(Alert, Device.building_id)
        .join(Device, Device.device_id == Alert.device_id)
        .order_by(Alert.detected_at.desc(), Alert.alert_id.desc())
        .limit(limit + 1)
    )
    if building_id is not None:
        stmt = stmt.where(Device.building_id == building_id)
    if device_id is not None:
        stmt = stmt.where(Alert.device_id == device_id)
    if cursor is not None:
        dt, aid = pagination.decode(cursor, sig, 2)
        stmt = stmt.where(tuple_(Alert.detected_at, Alert.alert_id) < tuple_(pagination.parse_dt(dt), aid))
    rows = db.execute(stmt).all()
    page, more = rows[:limit], len(rows) > limit
    data = [{
        "alert_id": a.alert_id, "message_id": a.message_id, "device_id": a.device_id, "building_id": b,
        "event_time": a.event_time, "detected_at": a.detected_at, "metric": "power_kw",
        "value": float(a.value_kw), "threshold": float(a.threshold_kw), "unit": "kW", "description": a.description,
    } for a, b in page]
    nxt = pagination.encode(sig, [page[-1][0].detected_at.isoformat(), page[-1][0].alert_id]) if more else None
    return data, nxt
