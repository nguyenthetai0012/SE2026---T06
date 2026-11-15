"""Unit test cho logic export với store GIẢ (in-memory), không cần DB.

Có chủ đích: các test này chỉ kiểm hợp đồng mà store giả TỰ mô phỏng. Thí nghiệm mutation trong
docs/testing/bt3-vt023/README.md cho thấy chúng vẫn pass khi guard ở PostgreSQL bị bỏ. Đây là minh hoạ cho
risk "mock che giấu contract sai với database"; guard thật được kiểm ở tests/integration/backend.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.exports import (
    ExportRequest, ExportRow, ExportTooLarge, IdempotencyConflict, Principal, StoredExport, create_export, render_csv,
)

T0 = datetime(2026, 10, 27, tzinfo=timezone.utc)
T3 = datetime(2026, 10, 27, 0, 3, tzinfo=timezone.utc)
OPS = Principal(client_id="ops", can_export=True, buildings=frozenset({"BLD-A"}))


class FakeStore:
    def __init__(self):
        self.rows: dict[tuple[str, str], StoredExport] = {}

    def find(self, client_id: str, key: str) -> StoredExport | None:
        return self.rows.get((client_id, key))

    def insert_if_absent(self, export: StoredExport) -> bool:
        k = (export.client_id, export.idempotency_key)
        if k in self.rows:
            return False
        self.rows[k] = export
        return True


def row(i: int, device: str = "A-01", value: str = "1") -> ExportRow:
    return ExportRow(message_id=f"m-{i}", device_id=device, building_id="BLD-A", metric="power_kw",
                     event_time=datetime(2026, 10, 27, 0, 0, i, tzinfo=timezone.utc),
                     received_at=datetime(2026, 10, 27, 0, 0, i, tzinfo=timezone.utc), interval_start=None,
                     value=Decimal(value), unit="kW", is_late=False, is_out_of_order=False)


class Source:
    def __init__(self, rows):
        self.rows, self.calls = rows, 0

    def __call__(self, building_id, metric, start, end, limit):
        self.calls += 1
        return self.rows[:limit]


REQ = ExportRequest(building_id="BLD-A", metric="power_kw", start=T0, end=T3)


def test_replay_returns_same_export_without_regenerating():
    store, src = FakeStore(), Source([row(1), row(2)])
    a, created_a = create_export(store, src, OPS, "key-unit-0001", REQ, now=T3, max_rows=10)
    b, created_b = create_export(store, src, OPS, "key-unit-0001", REQ, now=T3, max_rows=10)
    assert (created_a, created_b) == (True, False) and a == b and src.calls == 1


def test_same_key_different_request_conflicts():
    store = FakeStore()
    create_export(store, Source([row(1)]), OPS, "key-unit-0002", REQ, now=T3, max_rows=10)
    other = ExportRequest(building_id="BLD-A", metric="energy_kwh", start=T0, end=T3)
    with pytest.raises(IdempotencyConflict):
        create_export(store, Source([]), OPS, "key-unit-0002", other, now=T3, max_rows=10)


def test_too_large_stores_nothing():
    store = FakeStore()
    with pytest.raises(ExportTooLarge):
        create_export(store, Source([row(i) for i in range(5)]), OPS, "key-unit-0003", REQ, now=T3, max_rows=4)
    assert store.rows == {}


def test_request_hash_ignores_nothing_that_changes_the_result():
    a = ExportRequest(building_id="BLD-A", metric="power_kw", start=T0, end=T3)
    assert a.request_hash() == ExportRequest(building_id="BLD-A", metric="power_kw", start=T0, end=T3).request_hash()
    assert a.request_hash() != ExportRequest(building_id="BLD-A", metric="power_kw", start=T0,
                                             end=datetime(2026, 10, 27, 0, 2, tzinfo=timezone.utc)).request_hash()


def test_render_csv_header_decimal_and_formula_guard():
    text = render_csv([row(1, value="0.000000001"), row(2, device="-A1", value="12.500")]).decode()
    lines = text.splitlines()
    assert lines[0] == ("message_id,device_id,building_id,metric,event_time,received_at,interval_start,"
                        "value,unit,is_late,is_out_of_order")
    assert lines[1].split(",")[7] == "0.000000001"
    assert lines[2].split(",")[1] == "'-A1" and lines[2].split(",")[7] == "12.5"
