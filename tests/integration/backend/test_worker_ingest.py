"""Integration test cho worker ingestion (issue #37) trên PostgreSQL thật; ma trận theo docs/testing/mvp-acceptance.md.

Không cần broker: kiểm thẳng worker.ingest.ingest() và worker.consumer.handle(). Phần nối Paho/Mosquitto: chưa kiểm ở đây.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import Alert, Device, Reading
from worker.consumer import Stats, handle
from worker.ingest import ingest

from conftest import utc

A01 = "campus/v1/BLD-A/A-01/readings"
UUID_N = iter(range(1000, 10**6))


def mid() -> str:
    return f"00000000-0000-4000-8000-{next(UUID_N):012d}"


def power(ev="2026-10-27T00:01:00Z", value=5, device="A-01", building="BLD-A", **extra):
    p = {"schema_version": "1.0", "message_id": mid(), "building_id": building, "device_id": device,
         "event_time": ev, "metric": "power_kw", "value": value}
    p.update(extra)
    return p


def energy(start, ev, value=0.1, device="A-01", building="BLD-A"):
    return {"schema_version": "1.0", "message_id": mid(), "building_id": building, "device_id": device,
            "event_time": ev, "interval_start": start, "metric": "energy_kwh", "value": value}


def send(db, payload, received="2026-10-27T00:03:00Z", topic=None, retained=False):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    t = topic or f"campus/v1/{payload['building_id']}/{payload['device_id']}/readings" if isinstance(payload, dict) else (topic or A01)
    return ingest(db, t, raw, utc(received), retained)


def counts(db):
    return (db.scalar(select(func.count()).select_from(Reading)), db.scalar(select(func.count()).select_from(Alert)))


def last_seen(db, device="A-01"):
    db.expire_all()
    return db.get(Device, device).last_seen


def test_fixture_valid_ingest_matches_expected_totals(db, client, fixture_data):
    for m in fixture_data["messages"]:
        r = ingest(db, m["topic"], json.dumps(m["payload"]).encode(), utc(m["received_at"]))
        assert r.status == "accepted", (m, r)
    assert counts(db) == (len(fixture_data["messages"]), 2)
    q = fixture_data["query"]
    body = client.get("/api/v1/buildings/summary", params={"start": q["start"], "end": q["end"]}).json()["data"]
    by = {b["building_id"]: b for b in body}
    assert by["BLD-A"]["energy_kwh"] == pytest.approx(0.6, abs=1e-9)
    assert by["BLD-B"]["energy_kwh"] == pytest.approx(0.1, abs=1e-9)
    assert by["BLD-A"]["coverage"] == "complete"


def test_multiple_buildings_stored_and_queryable_by_api(db, client):
    assert send(db, power(building="BLD-A", device="A-01")).status == "accepted"
    assert send(db, power(building="BLD-B", device="B-01")).status == "accepted"
    data = client.get("/api/v1/devices/B-01/readings", params={"metric": "power_kw", "start": "2026-10-27T00:00:00Z",
                                                               "end": "2026-10-27T00:05:00Z"}).json()["data"]
    assert len(data) == 1 and data[0]["building_id"] == "BLD-B"


def test_duplicate_changes_nothing(db):
    p = power(value=12)
    assert send(db, p, received="2026-10-27T00:01:01Z").status == "accepted"
    before, seen = counts(db), last_seen(db)
    again = send(db, dict(reversed(list(p.items()))), received="2026-10-27T00:02:30Z")   # thứ tự key khác
    assert again.status == "duplicate"
    assert counts(db) == before and last_seen(db) == seen == utc("2026-10-27T00:01:01Z")


def test_conflicting_message_id_rejected_original_kept(db):
    p = power(value=12)
    send(db, p)
    r = send(db, {**p, "value": 13})
    assert (r.status, r.code) == ("rejected", "MESSAGE_ID_CONFLICT")
    assert db.get(Reading, p["message_id"]).value == 12


def test_same_device_metric_time_other_id_is_reading_conflict(db):
    send(db, power(value=5))
    r = send(db, power(value=6))
    assert (r.status, r.code) == ("rejected", "READING_CONFLICT")
    assert counts(db)[0] == 1


@pytest.mark.parametrize("mutate,code", [
    (lambda p: p.pop("value"), "MISSING_FIELD"),
    (lambda p: p.update(value="12"), "INVALID_VALUE"),
    (lambda p: p.update(value=True), "INVALID_VALUE"),
    (lambda p: p.update(value=-1), "INVALID_VALUE"),
    (lambda p: p.update(value=None), "INVALID_VALUE"),
    (lambda p: p.update(extra=1), "UNKNOWN_FIELD"),
    (lambda p: p.update(event_time="2026-10-27 00:01:00"), "INVALID_TIMESTAMP"),
    (lambda p: p.update(event_time="2026-10-27T00:01:00+07:00"), "INVALID_TIMESTAMP"),
    (lambda p: p.update(event_time="2026-10-27T00:03:06Z"), "FUTURE_EVENT_TIME"),
    (lambda p: p.update(schema_version="2.0"), "INVALID_SCHEMA_VERSION"),
    (lambda p: p.update(metric="voltage"), "INVALID_METRIC"),
    (lambda p: p.update(message_id="not-a-uuid"), "INVALID_MESSAGE_ID"),
    (lambda p: p.update(device_id="A 01"), "INVALID_ID"),
    (lambda p: p.update(interval_start="2026-10-27T00:00:00Z"), "INVALID_INTERVAL"),
    (lambda p: p.update(device_id="Z-99"), "TOPIC_MISMATCH"),
])
def test_invalid_payload_rejected_without_side_effects(db, mutate, code):
    p = power(value=12)
    mutate(p)
    before, seen = counts(db), last_seen(db)
    r = ingest(db, A01, json.dumps(p).encode(), utc("2026-10-27T00:03:00Z"))
    assert (r.status, r.code) == ("rejected", code)
    assert counts(db) == before and last_seen(db) == seen


@pytest.mark.parametrize("raw,code", [
    (b'{"a":', "INVALID_JSON"),
    (b"\xff\xfe", "INVALID_JSON"),
    (b"[1]", "INVALID_JSON"),
    (b'{"value": NaN}', "INVALID_VALUE"),
    (b'{"value": Infinity}', "INVALID_VALUE"),
    (b'{"value": 1, "value": 2}', "INVALID_JSON"),
    (b"{" + b" " * 5000 + b"}", "PAYLOAD_TOO_LARGE"),
])
def test_malformed_raw_payloads(db, raw, code):
    r = ingest(db, A01, raw, utc("2026-10-27T00:03:00Z"))
    assert (r.status, r.code) == ("rejected", code)
    assert counts(db) == (0, 0)


def test_topic_mismatch_unknown_device_and_retained(db):
    p = power()
    assert send(db, p, topic="campus/v1/BLD-B/A-01/readings").code == "TOPIC_MISMATCH"
    assert send(db, p, topic="campus/v2/BLD-A/A-01/readings").code == "TOPIC_MISMATCH"
    assert send(db, p, retained=True).code == "RETAINED_MESSAGE"
    unknown = power(device="Z-99")
    assert send(db, unknown).code == "UNKNOWN_DEVICE"
    wrong_building = power(device="B-01", building="BLD-A")
    assert send(db, wrong_building).code == "UNKNOWN_DEVICE"
    assert counts(db) == (0, 0)


def test_energy_requires_interval_and_ordered_bounds(db):
    p = energy("2026-10-27T00:00:00Z", "2026-10-27T00:01:00Z")
    p.pop("interval_start")
    assert send(db, p).code == "MISSING_FIELD"
    assert send(db, energy("2026-10-27T00:01:00Z", "2026-10-27T00:01:00Z")).code == "INVALID_INTERVAL"


def test_overlap_rejected_adjacent_allowed(db):
    assert send(db, energy("2026-10-27T00:00:00Z", "2026-10-27T00:01:00Z")).status == "accepted"
    r = send(db, energy("2026-10-27T00:00:30Z", "2026-10-27T00:01:30Z"))
    assert (r.status, r.code) == ("rejected", "INTERVAL_OVERLAP")
    assert send(db, energy("2026-10-27T00:01:00Z", "2026-10-27T00:02:00Z")).status == "accepted"
    assert counts(db)[0] == 2


def test_out_of_order_flag_and_latest_event_time_not_regressing(db):
    send(db, power("2026-10-27T00:03:00Z"), received="2026-10-27T00:03:01Z")
    send(db, power("2026-10-27T00:02:00Z"), received="2026-10-27T00:03:01Z")
    rows = {r.event_time: r for r in db.scalars(select(Reading))}
    assert rows[utc("2026-10-27T00:02:00Z")].is_out_of_order is True
    assert rows[utc("2026-10-27T00:02:00Z")].is_late is False       # age 61s <= 120s
    assert rows[utc("2026-10-27T00:03:00Z")].is_out_of_order is False
    db.expire_all()
    assert db.get(Device, "A-01").latest_event_time == utc("2026-10-27T00:03:00Z")


def test_late_boundary_and_event_time_preserved(db):
    ev = utc("2026-10-27T00:00:00Z")
    r1 = send(db, power("2026-10-27T00:00:00Z"), received="2026-10-27T00:02:00Z")
    r2 = send(db, power("2026-10-27T00:00:01Z"), received=(utc("2026-10-27T00:00:01Z") + timedelta(seconds=120, microseconds=1)).isoformat().replace("+00:00", "Z"))
    assert (r1.status, r2.status) == ("accepted", "accepted")
    first = db.scalars(select(Reading).where(Reading.event_time == ev)).one()
    second = db.scalars(select(Reading).where(Reading.event_time == utc("2026-10-27T00:00:01Z"))).one()
    assert first.is_late is False and second.is_late is True
    late = send(db, power("2026-10-27T00:00:30Z", value=11), received="2026-10-27T01:00:00Z")
    assert late.status == "accepted"
    row = db.scalars(select(Reading).where(Reading.event_time == utc("2026-10-27T00:00:30Z"))).one()
    assert row.is_late and row.event_time == utc("2026-10-27T00:00:30Z")
    assert db.scalar(select(func.count()).select_from(Alert)) == 1       # late vẫn sinh alert


@pytest.mark.parametrize("value,alerts", [(9.9, 0), (10, 0), (10.1, 1)])
def test_threshold_only_strictly_above_creates_alert(db, value, alerts):
    send(db, power(value=value))
    assert counts(db) == (1, alerts)


def test_energy_never_creates_alert(db):
    send(db, energy("2026-10-27T00:00:00Z", "2026-10-27T00:01:00Z", value=500))
    assert counts(db) == (1, 0)


def test_last_seen_and_resume_after_offline(db):
    send(db, power("2026-10-27T00:00:00Z"), received="2026-10-27T00:00:01Z")
    assert last_seen(db) == utc("2026-10-27T00:00:01Z")
    bad = power("2026-10-27T00:09:00Z", value="x")
    send(db, bad, received="2026-10-27T00:10:00Z")                          # invalid không phục hồi
    assert last_seen(db) == utc("2026-10-27T00:00:01Z")
    send(db, power("2026-10-27T00:10:00Z"), received="2026-10-27T00:10:01Z")
    assert last_seen(db) == utc("2026-10-27T00:10:01Z")


def test_value_precision_normalised_and_duplicate_still_detected(db):
    p = power(value=0.1234567891)
    assert send(db, p).status == "accepted"
    assert send(db, p).status == "duplicate"


def test_database_failure_is_not_swallowed_and_not_acked(db, engine, monkeypatch):
    stats = Stats()

    def boom(*a, **k):
        raise OperationalError("stmt", {}, Exception("db down"))
    monkeypatch.setattr("worker.consumer.ingest", boom)
    ack = handle(engine, stats, A01, json.dumps(power()).encode(), False)
    assert ack is False and stats.db_failures == 1 and counts(db) == (0, 0)


def test_handle_acks_rejected_and_counts_by_code(db, engine):
    stats = Stats()
    assert handle(engine, stats, A01, b"not json", False) is True
    assert handle(engine, stats, A01, json.dumps(power(), ).encode(), False, clock=lambda: utc("2026-10-27T00:03:00Z")) is True
    assert stats.counts["rejected:INVALID_JSON"] == 1 and stats.counts["accepted"] == 1
