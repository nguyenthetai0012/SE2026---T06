"""Ghi một bản tin hợp lệ vào DB trong MỘT transaction (docs/contracts/mvp-mqtt.md, mục Ingest).

Thứ tự: validate -> registry -> idempotency -> interval -> ghi. Bản tin bị từ chối không để lại dấu vết trong
readings/alerts/devices. Lỗi hạ tầng (DB) được ném ra ngoài để consumer quyết định, không bị nuốt thành 'rejected'.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Alert, Device, Reading

from .validate import Message, Rejected, validate

LATE_MULTIPLIER = 2        # late khi received_at - event_time > 2 * period (baseline Q8)


@dataclass(frozen=True)
class Result:
    status: str                 # accepted | duplicate | rejected
    code: str | None = None
    message_id: str | None = None


def _same_content(row: Reading, msg: Message) -> bool:
    return (row.device_id == msg.device_id and row.metric == msg.metric and row.event_time == msg.event_time
            and row.interval_start == msg.interval_start and row.value == msg.value)


def _apply(db: Session, msg: Message, received_at: datetime) -> Result:
    # Khóa dòng device để các bản tin cùng device được xử lý tuần tự (max/overlap/last_seen nhất quán).
    dev = db.scalars(select(Device).where(Device.device_id == msg.device_id).with_for_update()).one_or_none()
    if dev is None or dev.building_id != msg.building_id:
        raise Rejected("UNKNOWN_DEVICE", "device_id/building_id không có trong registry")

    existing = db.get(Reading, msg.message_id)
    if existing is not None:
        if _same_content(existing, msg):
            return Result("duplicate", message_id=msg.message_id)
        raise Rejected("MESSAGE_ID_CONFLICT", "cùng message_id nhưng nội dung khác")
    clash = db.scalar(select(Reading.message_id).where(
        Reading.device_id == msg.device_id, Reading.metric == msg.metric, Reading.event_time == msg.event_time))
    if clash is not None:
        raise Rejected("READING_CONFLICT", "đã có reading cùng device, metric, event_time với ID khác")

    if msg.metric == "energy_kwh":
        overlap = db.scalar(select(Reading.message_id).where(
            Reading.device_id == msg.device_id, Reading.metric == "energy_kwh",
            Reading.interval_start < msg.event_time, Reading.event_time > msg.interval_start).limit(1))
        if overlap is not None:
            raise Rejected("INTERVAL_OVERLAP", "interval chồng lấn interval đã lưu")

    prior_max = db.scalar(select(func.max(Reading.event_time)).where(
        Reading.device_id == msg.device_id, Reading.metric == msg.metric))
    is_late = (received_at - msg.event_time) > timedelta(seconds=LATE_MULTIPLIER * dev.period_seconds)
    is_out_of_order = prior_max is not None and msg.event_time < prior_max

    db.add(Reading(
        message_id=msg.message_id, device_id=msg.device_id, metric=msg.metric, event_time=msg.event_time,
        received_at=received_at, interval_start=msg.interval_start, value=msg.value,
        is_late=is_late, is_out_of_order=is_out_of_order, period_seconds=dev.period_seconds))
    db.flush()
    dev.last_seen = received_at if dev.last_seen is None else max(dev.last_seen, received_at)
    dev.latest_event_time = msg.event_time if dev.latest_event_time is None else max(dev.latest_event_time, msg.event_time)
    if msg.metric == "power_kw" and msg.value > dev.power_threshold_kw:
        db.add(Alert(
            alert_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"alert:{msg.message_id}")), message_id=msg.message_id,
            device_id=msg.device_id, event_time=msg.event_time, detected_at=received_at, value_kw=msg.value,
            threshold_kw=dev.power_threshold_kw, description=f"power_kw {msg.value} > {dev.power_threshold_kw} kW"))
    db.flush()
    return Result("accepted", message_id=msg.message_id)


def ingest(db: Session, topic: str, raw: bytes, received_at: datetime, retained: bool = False) -> Result:
    """Trả Result; chỉ ném ngoại lệ hạ tầng (OperationalError...) khi DB lỗi."""
    try:
        msg = validate(topic, raw, received_at, retained)
        result = _apply(db, msg, received_at)
        db.commit()
        return result
    except Rejected as exc:
        db.rollback()
        return Result("rejected", exc.code)
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""
        if constraint == "ex_readings_energy_no_overlap":
            return Result("rejected", "INTERVAL_OVERLAP")
        if constraint == "uq_readings_device_metric_event":
            return Result("rejected", "READING_CONFLICT")
        raise
    except Exception:
        db.rollback()
        raise
