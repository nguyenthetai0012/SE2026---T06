"""Kiểm tra payload/topic MQTT theo docs/contracts/mvp-mqtt.md (không đụng DB).

Thứ tự: retained -> size -> JSON -> schema -> topic. Mã lỗi đầu tiên theo thứ tự này được trả về.
Mã INVALID_VALUE, MESSAGE_ID_CONFLICT, READING_CONFLICT, INTERVAL_OVERLAP lấy từ contract; các mã còn lại
là tên nội bộ của worker (contract chưa đặt tên) và có thể đổi theo quyết định của nhóm.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal

MAX_PAYLOAD_BYTES = 4096
FUTURE_TOLERANCE = timedelta(seconds=5)
SCHEMA_VERSION = "1.0"
REQUIRED = ("schema_version", "message_id", "building_id", "device_id", "event_time", "metric", "value")
ALLOWED = set(REQUIRED) | {"interval_start"}
METRICS = ("power_kw", "energy_kwh")
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
TOPIC_RE = re.compile(r"^campus/v1/([^/]+)/([^/]+)/readings$")
SCALE = Decimal("0.000000001")      # Numeric(24, 9)
MAX_VALUE = Decimal(10) ** 14


class Rejected(Exception):
    """Bản tin bị từ chối: không ghi reading/alert, không cập nhật last_seen."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Message:
    message_id: str
    building_id: str
    device_id: str
    event_time: datetime
    metric: str
    value: Decimal
    interval_start: datetime | None


def _no_duplicate_keys(pairs):
    seen: dict = {}
    for key, val in pairs:
        if key in seen:
            raise Rejected("INVALID_JSON", f"khóa JSON lặp: {key}")
        seen[key] = val
    return seen


def _bad_constant(name: str):
    raise Rejected("INVALID_VALUE", f"hằng số không hợp lệ: {name}")


def _parse_ts(value, name: str) -> datetime:
    if not isinstance(value, str) or not TS_RE.match(value):
        raise Rejected("INVALID_TIMESTAMP", f"{name} phải là ISO 8601 UTC kết thúc bằng 'Z', tối đa microsecond")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise Rejected("INVALID_TIMESTAMP", f"{name} không phải thời điểm hợp lệ") from exc


def _parse_uuid(value) -> str:
    if not isinstance(value, str) or len(value) != 36:
        raise Rejected("INVALID_MESSAGE_ID", "message_id phải là UUID dạng chuỗi")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise Rejected("INVALID_MESSAGE_ID", "message_id phải là UUID dạng chuỗi") from exc
    return str(parsed)


def parse_payload(raw: bytes) -> dict:
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise Rejected("PAYLOAD_TOO_LARGE", f"{len(raw)} > {MAX_PAYLOAD_BYTES} byte")
    try:
        text = raw.decode("utf-8")
        data = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_float=Decimal,
                          parse_constant=_bad_constant)
    except Rejected:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise Rejected("INVALID_JSON", "không phải UTF-8 JSON hợp lệ") from exc
    if not isinstance(data, dict):
        raise Rejected("INVALID_JSON", "payload phải là JSON object")
    return data


def validate(topic: str, raw: bytes, received_at: datetime, retained: bool = False) -> Message:
    if retained:
        raise Rejected("RETAINED_MESSAGE", "bản tin retained bị từ chối")
    data = parse_payload(raw)

    for key in data:
        if key not in ALLOWED:
            raise Rejected("UNKNOWN_FIELD", f"trường không được hỗ trợ: {key}")
    for key in REQUIRED:
        if key not in data:
            raise Rejected("MISSING_FIELD", f"thiếu trường bắt buộc: {key}")
    if any(v is None for v in data.values()):
        raise Rejected("INVALID_VALUE", "không chấp nhận null")
    if data["schema_version"] != SCHEMA_VERSION:
        raise Rejected("INVALID_SCHEMA_VERSION", "schema_version phải là '1.0'")

    message_id = _parse_uuid(data["message_id"])
    for key in ("building_id", "device_id"):
        if not isinstance(data[key], str) or not ID_RE.match(data[key]):
            raise Rejected("INVALID_ID", f"{key} sai định dạng (1-64 ký tự A-Z a-z 0-9 _ -)")
    metric = data["metric"]
    if not isinstance(metric, str) or metric not in METRICS:
        raise Rejected("INVALID_METRIC", "metric phải là power_kw hoặc energy_kwh")

    raw_value = data["value"]
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, Decimal)):
        raise Rejected("INVALID_VALUE", "value phải là số, không phải bool/chuỗi")
    value = Decimal(raw_value)
    if not value.is_finite() or value < 0 or value >= MAX_VALUE:
        raise Rejected("INVALID_VALUE", "value phải là số hữu hạn, không âm, trong giới hạn lưu trữ")
    value = value.quantize(SCALE, rounding=ROUND_HALF_EVEN)

    event_time = _parse_ts(data["event_time"], "event_time")
    if event_time > received_at + FUTURE_TOLERANCE:
        raise Rejected("FUTURE_EVENT_TIME", "event_time vượt received_at + 5s")
    interval_start = None
    if metric == "energy_kwh":
        if "interval_start" not in data:
            raise Rejected("MISSING_FIELD", "energy_kwh bắt buộc interval_start")
        interval_start = _parse_ts(data["interval_start"], "interval_start")
        if not interval_start < event_time:
            raise Rejected("INVALID_INTERVAL", "interval_start phải nhỏ hơn event_time")
    elif "interval_start" in data:
        raise Rejected("INVALID_INTERVAL", "power_kw không được có interval_start")

    match = TOPIC_RE.match(topic)
    if match is None or (match.group(1), match.group(2)) != (data["building_id"], data["device_id"]):
        raise Rejected("TOPIC_MISMATCH", "topic không khớp building_id/device_id trong payload")

    return Message(message_id, data["building_id"], data["device_id"], event_time, metric, value, interval_start)
