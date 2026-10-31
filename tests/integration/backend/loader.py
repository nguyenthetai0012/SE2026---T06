"""Chỉ dùng cho test: nạp bộ fixture vào DB để kiểm contract đọc.

KHÔNG phải worker ingestion (bước 2B). Ở đây chỉ áp các quy tắc tối thiểu đã ghi trong
docs/contracts/mvp-mqtt.md để điền cột dẫn xuất (late, out-of-order, last_seen, latest_event_time, alert);
validation/idempotency/overlap đầy đủ thuộc worker và được kiểm riêng ở 2B."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Device, Reading


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def add_reading(db: Session, *, message_id: str, device_id: str, metric: str, event_time: str, received_at: str,
                value, interval_start: str | None = None) -> Reading:
    dev = db.get(Device, device_id)
    ev, rec = utc(event_time), utc(received_at)
    prior_max = db.scalar(select(Reading.event_time).where(Reading.device_id == device_id, Reading.metric == metric)
                          .order_by(Reading.event_time.desc()).limit(1))
    row = Reading(
        message_id=message_id, device_id=device_id, metric=metric, event_time=ev, received_at=rec,
        interval_start=utc(interval_start) if interval_start else None, value=Decimal(str(value)),
        is_late=(rec - ev) > timedelta(seconds=2 * dev.period_seconds),
        is_out_of_order=prior_max is not None and ev < prior_max, period_seconds=dev.period_seconds,
    )
    db.add(row)
    db.flush()
    dev.last_seen = max(filter(None, [dev.last_seen, rec]))
    dev.latest_event_time = max(filter(None, [dev.latest_event_time, ev]))
    if metric == "power_kw" and Decimal(str(value)) > dev.power_threshold_kw:
        db.add(Alert(
            alert_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"alert:{message_id}")), message_id=message_id,
            device_id=device_id, event_time=ev, detected_at=rec, value_kw=Decimal(str(value)),
            threshold_kw=dev.power_threshold_kw, description=f"power_kw {value} > {dev.power_threshold_kw} kW",
        ))
    db.flush()
    return row


def load_fixture(db: Session, fixture: dict, skip=lambda m: False) -> int:
    n = 0
    for m in fixture["messages"]:
        if skip(m):
            continue
        p = m["payload"]
        add_reading(db, message_id=p["message_id"], device_id=p["device_id"], metric=p["metric"],
                    event_time=p["event_time"], received_at=m["received_at"], value=p["value"],
                    interval_start=p.get("interval_start"))
        n += 1
    db.commit()
    return n
