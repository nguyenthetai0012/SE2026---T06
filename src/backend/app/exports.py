"""Xuất dữ liệu readings theo building (BT3 VT-023).

Bất biến cần bảo vệ: mỗi (client_id, Idempotency-Key) ứng với ĐÚNG MỘT export, và export chỉ chứa
readings của building nằm trong scope của client đó. Guard đồng thời nằm ở PostgreSQL
(UNIQUE uq_exports_client_key + INSERT ... ON CONFLICT DO NOTHING), không nằm ở bộ nhớ ứng dụng.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .models import Device, Export, Reading
from .params import UNIT

CSV_COLUMNS = ("message_id", "device_id", "building_id", "metric", "event_time", "received_at",
               "interval_start", "value", "unit", "is_late", "is_out_of_order")
_FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")


class IdempotencyConflict(Exception):
    """Cùng Idempotency-Key nhưng nội dung request khác."""


class ExportTooLarge(Exception):
    pass


@dataclass(frozen=True)
class Principal:
    client_id: str
    can_export: bool
    buildings: frozenset[str]


@dataclass(frozen=True)
class ExportRequest:
    building_id: str
    metric: str
    start: datetime
    end: datetime

    def request_hash(self) -> str:
        canon = {"building_id": self.building_id, "metric": self.metric,
                 "start": _iso(self.start), "end": _iso(self.end)}
        return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ExportRow:
    message_id: str
    device_id: str
    building_id: str
    metric: str
    event_time: datetime
    received_at: datetime
    interval_start: datetime | None
    value: Decimal
    unit: str
    is_late: bool
    is_out_of_order: bool


@dataclass(frozen=True)
class StoredExport:
    export_id: uuid.UUID
    client_id: str
    idempotency_key: str
    request_hash: str
    building_id: str
    metric: str
    start: datetime
    end: datetime
    row_count: int
    content_sha256: str
    content: bytes
    created_at: datetime


class ExportStore(Protocol):
    def find(self, client_id: str, key: str) -> StoredExport | None: ...

    def insert_if_absent(self, export: StoredExport) -> bool: ...


RowSource = Callable[[str, str, datetime, datetime, int], list[ExportRow]]


def create_export(store: ExportStore, source: RowSource, principal: Principal, key: str, req: ExportRequest,
                  *, now: datetime, max_rows: int) -> tuple[StoredExport, bool]:
    """Trả (export, created). created=False khi là replay của cùng key."""
    want = req.request_hash()
    existing = store.find(principal.client_id, key)
    if existing is not None:
        return _replay(existing, want), False
    rows = source(req.building_id, req.metric, req.start, req.end, max_rows + 1)
    if len(rows) > max_rows:
        raise ExportTooLarge()
    content = render_csv(rows)
    export = StoredExport(
        export_id=uuid.uuid4(), client_id=principal.client_id, idempotency_key=key, request_hash=want,
        building_id=req.building_id, metric=req.metric, start=req.start, end=req.end, row_count=len(rows),
        content_sha256=hashlib.sha256(content).hexdigest(), content=content, created_at=now,
    )
    if store.insert_if_absent(export):
        return export, True
    # Request đồng thời khác cùng key đã thắng: trả đúng export của nó, không tạo bản thứ hai.
    existing = store.find(principal.client_id, key)
    if existing is None:  # pragma: no cover - chỉ xảy ra nếu DB vi phạm READ COMMITTED
        raise RuntimeError("idempotency insert bị chặn nhưng không thấy bản ghi đã có")
    return _replay(existing, want), False


def _replay(existing: StoredExport, want_hash: str) -> StoredExport:
    if existing.request_hash != want_hash:
        raise IdempotencyConflict()
    return existing


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(d: Decimal) -> str:
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _cell(v: str) -> str:
    # Chống CSV/formula injection khi mở bằng bảng tính: ID hợp lệ có thể bắt đầu bằng '-'.
    return "'" + v if v.startswith(_FORMULA_PREFIX) else v


def render_csv(rows: list[ExportRow]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(CSV_COLUMNS)
    for r in rows:
        w.writerow([_cell(r.message_id), _cell(r.device_id), _cell(r.building_id), r.metric, _iso(r.event_time),
                    _iso(r.received_at), _iso(r.interval_start) if r.interval_start else "", _decimal(r.value),
                    r.unit, "true" if r.is_late else "false", "true" if r.is_out_of_order else "false"])
    return buf.getvalue().encode("utf-8")


# ------------------------------------------------------------------ PostgreSQL
def _to_stored(e: Export) -> StoredExport:
    return StoredExport(export_id=e.export_id, client_id=e.client_id, idempotency_key=e.idempotency_key,
                        request_hash=e.request_hash, building_id=e.building_id, metric=e.metric, start=e.start_at,
                        end=e.end_at, row_count=e.row_count, content_sha256=e.content_sha256,
                        content=bytes(e.content), created_at=e.created_at)


class PgExportStore:
    def __init__(self, db: Session):
        self.db = db

    def find(self, client_id: str, key: str) -> StoredExport | None:
        e = self.db.scalar(select(Export).where(Export.client_id == client_id, Export.idempotency_key == key)
                           .execution_options(populate_existing=True))
        return _to_stored(e) if e is not None else None

    def insert_if_absent(self, export: StoredExport) -> bool:
        stmt = (
            pg_insert(Export)
            .values(export_id=export.export_id, client_id=export.client_id, idempotency_key=export.idempotency_key,
                    request_hash=export.request_hash, building_id=export.building_id, metric=export.metric,
                    start_at=export.start, end_at=export.end, row_count=export.row_count,
                    content_sha256=export.content_sha256, content=export.content, created_at=export.created_at)
            .on_conflict_do_nothing(constraint="uq_exports_client_key")
            .returning(Export.export_id)
        )
        return self.db.execute(stmt).first() is not None


def pg_row_source(db: Session) -> RowSource:
    def fetch(building_id: str, metric: str, start: datetime, end: datetime, limit: int) -> list[ExportRow]:
        # Scope áp ngay trong SQL (JOIN devices theo building), không lọc sau ở Python.
        stmt = (
            select(Reading, Device.building_id)
            .join(Device, Device.device_id == Reading.device_id)
            .where(Device.building_id == building_id, Reading.metric == metric,
                   Reading.event_time >= start, Reading.event_time < end)
            .order_by(Reading.event_time, Reading.message_id)
            .limit(limit)
        )
        return [ExportRow(message_id=r.message_id, device_id=r.device_id, building_id=b, metric=r.metric,
                          event_time=r.event_time, received_at=r.received_at, interval_start=r.interval_start,
                          value=r.value, unit=UNIT[r.metric], is_late=r.is_late, is_out_of_order=r.is_out_of_order)
                for r, b in db.execute(stmt)]
    return fetch


def get_owned_export(db: Session, principal: Principal, export_id: uuid.UUID) -> StoredExport | None:
    """Chỉ client tạo ra export, và building vẫn còn trong scope hiện tại, mới thấy được nó."""
    e = db.scalar(select(Export).where(Export.export_id == export_id, Export.client_id == principal.client_id))
    if e is None or e.building_id not in principal.buildings:
        return None
    return _to_stored(e)
