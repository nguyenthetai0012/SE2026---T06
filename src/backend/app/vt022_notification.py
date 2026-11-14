"""Harness cá nhân VT-022; không phải MQTT worker của dự án."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Alert, Device, Reading

MAX_INPUT_BYTES = 4096


@dataclass(frozen=True)
class ProcessingResult:
    message_id: str
    alert_id: str | None
    notification_status: str


def process_reading(engine, event, sender):
    """Lưu reading + alert trong transaction; sender chỉ chạy sau commit.

    Harness chưa thực hiện idempotency, MQTT hoặc gửi lại bền vững.
    """
    if not isinstance(event, dict) or set(event) != {"message_id", "device_id", "event_time", "value_kw"}:
        raise ValueError("invalid event fields")
    try:
        encoded = json.dumps(event, default=str, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_INPUT_BYTES:
            raise ValueError("event exceeds size limit")
        message_id = str(UUID(event["message_id"]))
        device_id = event["device_id"]
        event_time = event["event_time"]
        raw_value = event["value_kw"]
        if not isinstance(device_id, str) or not isinstance(event_time, datetime) or event_time.utcoffset() is None:
            raise ValueError("invalid device or timestamp")
        if isinstance(raw_value, (bool, str)):
            raise ValueError("invalid value type")
        value = Decimal(str(raw_value))
        if not value.is_finite() or value < 0:
            raise ValueError("value must be finite and nonnegative")
    except (TypeError, AttributeError, InvalidOperation) as exc:
        raise ValueError("invalid event") from exc

    now = datetime.now(timezone.utc)
    alert = None
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            device = session.get(Device, device_id)
            if device is None:
                raise ValueError("unknown device")
            previous = session.scalar(select(func.max(Reading.event_time)).where(
                Reading.device_id == device_id, Reading.metric == "power_kw"))
            reading = Reading(message_id=message_id, device_id=device_id, metric="power_kw",
                              event_time=event_time, received_at=now, interval_start=None,
                              value=value, is_late=(now - event_time).total_seconds() > 2 * device.period_seconds,
                              is_out_of_order=previous is not None and event_time < previous,
                              period_seconds=device.period_seconds)
            session.add(reading)
            session.flush()
            if value > device.power_threshold_kw:
                alert = Alert(alert_id=message_id, message_id=message_id, device_id=device_id,
                              event_time=event_time, detected_at=now, value_kw=value,
                              threshold_kw=device.power_threshold_kw, description="Power threshold exceeded")
                session.add(alert)
        if alert is None:
            return ProcessingResult(message_id, None, "not_required")
        try:
            sender(alert)
        except Exception:
            return ProcessingResult(message_id, alert.alert_id, "failed")
        return ProcessingResult(message_id, alert.alert_id, "sent")
