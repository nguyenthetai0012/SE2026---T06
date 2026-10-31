"""Cursor opaque: mã hóa khóa sắp xếp cuối + chữ ký truy vấn, kiểm tra TRƯỚC khi chạy SQL.
Cursor không mang quyền truy cập và không được tin cậy: chỉ được dùng nếu cấu trúc/kiểu hợp lệ và chữ ký khớp."""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime

from .errors import invalid_cursor


def signature(kind: str, **query) -> str:
    blob = json.dumps({"kind": kind, **query}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def encode(sig: str, key: list[str]) -> str:
    raw = json.dumps({"v": 1, "s": sig, "k": key}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode(cursor: str, sig: str, parts: int) -> list[str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        obj = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if not isinstance(obj, dict) or obj.get("v") != 1 or obj.get("s") != sig:
            raise ValueError
        key = obj["k"]
        if not isinstance(key, list) or len(key) != parts or not all(isinstance(x, str) and 0 < len(x) <= 80 for x in key):
            raise ValueError
        return key
    except (ValueError, KeyError, TypeError):
        raise invalid_cursor() from None


def parse_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise invalid_cursor() from None
    if dt.tzinfo is None:
        raise invalid_cursor()
    return dt
