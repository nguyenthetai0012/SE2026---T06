"""GET /api/v1/buildings/summary: oracle fixture + biên + coverage + null khác 0."""
from __future__ import annotations

import pytest
from loader import add_reading, load_fixture

BASE = "/api/v1/buildings/summary"
RANGE = "start=2026-10-27T00:00:00Z&end=2026-10-27T00:02:00Z"


def by_building(resp):
    return {b["building_id"]: b for b in resp.json()["data"]}


def test_fixture_matches_oracle(client, db, fixture_data):
    assert load_fixture(db, fixture_data) == 12
    r = client.get(f"{BASE}?{RANGE}")
    assert r.status_code == 200
    got = by_building(r)
    exp = fixture_data["expected"]
    for b, kwh in exp["building_energy_kwh"].items():
        assert got[b]["energy_kwh"] == pytest.approx(kwh, abs=1e-9)
        assert got[b]["coverage_ratio"] == pytest.approx(exp["coverage_ratio"][b], abs=1e-9)
        assert got[b]["coverage"] == "complete" and got[b]["unit"] == "kWh"
        assert got[b]["data_stale"] is False
    assert (got["BLD-A"]["included_interval_count"], got["BLD-B"]["included_interval_count"]) == (4, 2)
    assert r.json()["meta"] == {"generated_at": "2026-10-27T00:03:00Z", "start": "2026-10-27T00:00:00Z",
                                "end": "2026-10-27T00:02:00Z", "building_id": None, "next_cursor": None}
    assert list(got) == ["BLD-A", "BLD-B"]


def test_building_filter_and_unknown_building(client, db, fixture_data):
    load_fixture(db, fixture_data)
    one = client.get(f"{BASE}?{RANGE}&building_id=BLD-B").json()
    assert [b["building_id"] for b in one["data"]] == ["BLD-B"] and one["meta"]["building_id"] == "BLD-B"
    r = client.get(f"{BASE}?{RANGE}&building_id=BLD-Z")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_missing_interval_gives_partial(client, db, fixture_data):
    last_a02_energy = [m for m in fixture_data["messages"]
                       if m["payload"]["device_id"] == "A-02" and m["payload"]["metric"] == "energy_kwh"][-1]
    load_fixture(db, fixture_data, skip=lambda m: m is last_a02_energy)
    a = by_building(client.get(f"{BASE}?{RANGE}"))["BLD-A"]
    assert a["energy_kwh"] == pytest.approx(0.5, abs=1e-9)
    assert a["coverage"] == "partial" and a["coverage_ratio"] == pytest.approx(0.75)
    assert a["included_interval_count"] == 3


def test_disabled_device_excluded_from_total_and_coverage(client, db, fixture_data):
    load_fixture(db, fixture_data)
    db.execute(__import__("sqlalchemy").text("UPDATE devices SET enabled=false WHERE device_id='A-02'"))
    db.commit()
    a = by_building(client.get(f"{BASE}?{RANGE}"))["BLD-A"]
    assert a["energy_kwh"] == pytest.approx(0.4, abs=1e-9)          # chỉ A-01
    assert a["included_interval_count"] == 2
    assert a["coverage_ratio"] == pytest.approx(1.0) and a["coverage"] == "complete"   # không vượt 1


def test_no_data_is_null_not_zero_and_zero_value_is_zero(client, db):
    r = by_building(client.get(f"{BASE}?{RANGE}"))
    for b in r.values():
        assert b["energy_kwh"] is None and b["coverage"] == "none" and b["coverage_ratio"] == 0
        assert b["included_interval_count"] == 0 and b["data_stale"] is True       # chưa thiết bị nào gửi
    for i, (s, e) in enumerate((("00:00:00", "00:01:00"), ("00:01:00", "00:02:00"))):
        add_reading(db, message_id=f"00000000-0000-4000-8000-0000000001{i:02d}", device_id="B-01", metric="energy_kwh",
                    event_time=f"2026-10-27T{e}Z", received_at=f"2026-10-27T{e}Z", interval_start=f"2026-10-27T{s}Z", value=0)
    db.commit()
    b = by_building(client.get(f"{BASE}?{RANGE}"))["BLD-B"]
    assert b["energy_kwh"] == 0 and b["coverage"] == "complete" and b["included_interval_count"] == 2


def test_building_without_enabled_devices(client, db):
    db.execute(__import__("sqlalchemy").text("UPDATE devices SET enabled=false WHERE building_id='BLD-B'"))
    db.commit()
    b = by_building(client.get(f"{BASE}?{RANGE}"))["BLD-B"]
    assert (b["energy_kwh"], b["coverage"], b["coverage_ratio"], b["data_stale"]) == (None, "none", 0, False)


def test_boundaries_use_whole_intervals_only(client, db, fixture_data):
    load_fixture(db, fixture_data)
    # end = 00:01:00: chỉ interval [00:00,00:01) kết thúc đúng end được tính (event_time <= end).
    a = by_building(client.get(f"{BASE}?start=2026-10-27T00:00:00Z&end=2026-10-27T00:01:00Z"))["BLD-A"]
    assert a["included_interval_count"] == 2 and a["energy_kwh"] == pytest.approx(0.3, abs=1e-9)
    # start giữa interval: interval bị cắt biên không được chia tỷ lệ, bị loại.
    a = by_building(client.get(f"{BASE}?start=2026-10-27T00:00:30Z&end=2026-10-27T00:02:00Z"))["BLD-A"]
    assert a["included_interval_count"] == 2 and a["coverage"] == "partial"


def test_summary_stale_when_any_enabled_device_stale(client, db, fixture_data, clock):
    load_fixture(db, fixture_data)
    from datetime import timedelta
    clock.value = clock.value + timedelta(minutes=10)
    got = by_building(client.get(f"{BASE}?{RANGE}"))
    assert got["BLD-A"]["data_stale"] is True and got["BLD-B"]["data_stale"] is True


@pytest.mark.parametrize("qs", [
    "start=2026-10-27T00:00:00Z",                                                # thiếu end
    "start=2026-10-27T00:02:00Z&end=2026-10-27T00:02:00Z",                       # start == end
    "start=2026-10-27T00:03:00Z&end=2026-10-27T00:02:00Z",                       # start > end
    "start=2026-10-27T00:00:00%2B07:00&end=2026-10-27T01:00:00Z",                # timezone khác Z
    "start=2026-10-27T00:00:00&end=2026-10-27T01:00:00Z",                        # không timezone
    "start=2026-10-27T00:00:00Z&end=2026-10-27T01:00:00Z&foo=1",                 # tham số lạ
    "start=2026-10-27T00:00:00Z&start=2026-10-27T00:00:01Z&end=2026-10-27T01:00:00Z",   # lặp
    "start=2026-13-27T00:00:00Z&end=2026-10-27T01:00:00Z",                       # ngày sai
    "start=2026-10-27T00:00:00Z&end=2026-10-27T01:00:00Z&building_id=bad%20id",  # id sai format
])
def test_invalid_queries_are_422_envelope(client, qs):
    r = client.get(f"{BASE}?{qs}")
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "INVALID_QUERY" and err["message"] and err["request_id"]
    assert set(r.json()) == {"error"}
