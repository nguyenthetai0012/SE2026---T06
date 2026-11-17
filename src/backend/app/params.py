"""Phân tích query parameter chặt chẽ: tham số lạ, lặp, timestamp không phải UTC 'Z' đều trả 422."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import Request

from .config import DEFAULT_LIMIT, MAX_LIMIT
from .errors import invalid_query

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
METRICS = ("power_kw", "energy_kwh")
UNIT = {"power_kw": "kW", "energy_kwh": "kWh"}


def read_query(request: Request, allowed: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in request.query_params.keys():
        if key not in allowed:
            raise invalid_query(f"tham số không được hỗ trợ: {key}")
    for key in allowed:
        values = request.query_params.getlist(key)
        if len(values) > 1:
            raise invalid_query(f"tham số bị lặp: {key}")
        if values:
            out[key] = values[0]
    return out


def need(q: dict[str, str], key: str) -> str:
    if key not in q or q[key] == "":
        raise invalid_query(f"thiếu tham số bắt buộc: {key}")
    return q[key]


def parse_id(value: str, name: str) -> str:
    if not ID_RE.match(value):
        raise invalid_query(f"{name} sai định dạng (1-64 ký tự A-Z a-z 0-9 _ -)")
    return value


def parse_ts(value: str, name: str) -> datetime:
    if not TS_RE.match(value):
        raise invalid_query(f"{name} phải là ISO 8601 UTC kết thúc bằng 'Z'")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise invalid_query(f"{name} không phải thời điểm hợp lệ") from exc


def parse_range(q: dict[str, str]) -> tuple[datetime, datetime]:
    start, end = parse_ts(need(q, "start"), "start"), parse_ts(need(q, "end"), "end")
    if not start < end:
        raise invalid_query("start must be earlier than end")
    return start, end


def parse_limit(q: dict[str, str]) -> int:
    raw = q.get("limit")
    if raw is None:
        return DEFAULT_LIMIT
    if not re.fullmatch(r"[0-9]{1,6}", raw) or not 1 <= int(raw) <= MAX_LIMIT:
        raise invalid_query(f"limit phải là số nguyên từ 1 đến {MAX_LIMIT}")
    return int(raw)


def parse_metric(q: dict[str, str]) -> str:
    metric = need(q, "metric")
    if metric not in METRICS:
        raise invalid_query("metric phải là power_kw hoặc energy_kwh")
    return metric


# Mô tả query parameter cho OpenAPI (docs/contracts/mvp-api.md). Chỉ dùng qua openapi_extra để sinh schema;
# việc validate vẫn do read_query/parse_* ở trên, nên mã lỗi và thông báo không đổi.
def _ts(desc: str) -> dict:
    return {"type": "string", "format": "date-time", "pattern": TS_RE.pattern, "description": desc}


def _id(desc: str) -> dict:
    return {"type": "string", "minLength": 1, "maxLength": 64, "pattern": ID_RE.pattern, "description": desc}


_QUERY_SPECS: dict[str, tuple[bool, dict]] = {
    "start": (True, _ts("Mốc đầu, ISO 8601 UTC kết thúc bằng 'Z'; phải nhỏ hơn end.")),
    "end": (True, _ts("Mốc cuối, ISO 8601 UTC kết thúc bằng 'Z'.")),
    "metric": (True, {"type": "string", "enum": list(METRICS), "description": "Thông số cần lấy lịch sử."}),
    "building_id": (False, _id("Lọc theo tòa nhà; đúng định dạng nhưng không tồn tại -> 404.")),
    "device_id": (False, _id("Lọc theo thiết bị; không thuộc building_id -> 422 FILTER_MISMATCH.")),
    "limit": (False, {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT, "default": DEFAULT_LIMIT,
                      "description": "Số bản ghi tối đa mỗi trang."}),
    "cursor": (False, {"type": "string", "description": "Cursor opaque lấy từ meta.next_cursor của trang trước."}),
}


def openapi_query(*names: str) -> dict:
    """openapi_extra cho một route: khai báo đúng các tên mà route đó truyền vào read_query."""
    return {"parameters": [
        {"name": n, "in": "query", "required": _QUERY_SPECS[n][0], "schema": _QUERY_SPECS[n][1]} for n in names
    ]}
