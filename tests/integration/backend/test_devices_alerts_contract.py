"""GET /devices, /devices/{id}/readings, /alerts, /health/ready."""
from __future__ import annotations

from datetime import timedelta

import pytest
from loader import add_reading, load_fixture, utc
from sqlalchemy import text

H = "/api/v1/devices/A-01/readings"
RNG = "start=2026-10-27T00:00:00Z&end=2026-10-27T00:03:00Z"


def test_devices_list_status_and_meta(client, db, fixture_data):
    load_fixture(db, fixture_data)
    r = client.get("/api/v1/devices?building_id=BLD-A")
    assert r.status_code == 200
    body = r.json()
    assert [d["device_id"] for d in body["data"]] == ["A-01", "A-02"]
    a1 = body["data"][0]
    assert a1 == {"device_id": "A-01", "building_id": "BLD-A", "name": "Meter A1", "enabled": True, "status": "online",
                  "last_seen": "2026-10-27T00:02:01Z", "latest_event_time": "2026-10-27T00:02:00Z",
                  "data_stale": False, "period_seconds": 60}
    assert body["meta"] == {"generated_at": "2026-10-27T00:03:00Z", "building_id": "BLD-A", "next_cursor": None}


def test_offline_and_stale_share_the_same_boundary(client, db, clock):
    add_reading(db, message_id="00000000-0000-4000-8000-000000000201", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:00:00Z", received_at="2026-10-27T00:00:00Z", value=1)
    db.commit()
    t0 = utc("2026-10-27T00:00:00Z")
    for delta, status, stale in ((timedelta(seconds=180) - timedelta(microseconds=1), "online", False),
                                 (timedelta(seconds=180), "offline", True)):
        clock.value = t0 + delta
        a1 = next(d for d in client.get("/api/v1/devices").json()["data"] if d["device_id"] == "A-01")
        assert (a1["status"], a1["data_stale"]) == (status, stale), delta


def test_unknown_disabled_and_stale_but_online(client, db, clock):
    # Chưa gửi lần nào -> unknown + stale; disabled ưu tiên.
    data = {d["device_id"]: d for d in client.get("/api/v1/devices").json()["data"]}
    assert (data["A-01"]["status"], data["A-01"]["data_stale"], data["A-01"]["last_seen"]) == ("unknown", True, None)
    db.execute(text("UPDATE devices SET enabled=false WHERE device_id='A-02'"))
    db.commit()
    assert next(d for d in client.get("/api/v1/devices").json()["data"] if d["device_id"] == "A-02")["status"] == "disabled"
    # Reading cũ vừa đến: online (last_seen mới) nhưng data_stale (event_time cũ).
    add_reading(db, message_id="00000000-0000-4000-8000-000000000202", device_id="B-01", metric="power_kw",
                event_time="2026-10-26T20:00:00Z", received_at="2026-10-27T00:02:59Z", value=1)
    db.commit()
    b1 = next(d for d in client.get("/api/v1/devices").json()["data"] if d["device_id"] == "B-01")
    assert (b1["status"], b1["data_stale"]) == ("online", True)


def test_devices_pagination_has_no_gaps_or_duplicates(client, db):
    seen, cursor = [], None
    for _ in range(5):
        r = client.get("/api/v1/devices?limit=2" + (f"&cursor={cursor}" if cursor else ""))
        assert r.status_code == 200
        seen += [d["device_id"] for d in r.json()["data"]]
        cursor = r.json()["meta"]["next_cursor"]
        if cursor is None:
            break
    assert seen == ["A-01", "A-02", "B-01"]


def test_history_sorted_by_event_time_and_window_is_half_open(client, db, fixture_data):
    load_fixture(db, fixture_data)
    all_ = client.get(f"{H}?metric=power_kw&{RNG}").json()
    assert [r["event_time"] for r in all_["data"]] == ["2026-10-27T00:01:00Z", "2026-10-27T00:02:00Z"]
    assert all_["meta"] == {"generated_at": "2026-10-27T00:03:00Z", "device_id": "A-01", "metric": "power_kw",
                            "start": "2026-10-27T00:00:00Z", "end": "2026-10-27T00:03:00Z", "next_cursor": None}
    first = all_["data"][0]
    assert first["unit"] == "kW" and first["building_id"] == "BLD-A" and first["interval_start"] is None
    assert (first["is_late"], first["is_out_of_order"]) == (False, False)
    # start == event_time được lấy; end == event_time bị loại.
    one = client.get(f"{H}?metric=power_kw&start=2026-10-27T00:01:00Z&end=2026-10-27T00:02:00Z").json()["data"]
    assert [r["event_time"] for r in one] == ["2026-10-27T00:01:00Z"]
    e = client.get(f"{H}?metric=energy_kwh&{RNG}").json()["data"]
    assert [x["unit"] for x in e] == ["kWh", "kWh"] and e[0]["interval_start"] == "2026-10-27T00:00:00Z"


def test_history_pagination_and_cursor_signature(client, db, fixture_data):
    load_fixture(db, fixture_data)
    p1 = client.get(f"{H}?metric=power_kw&{RNG}&limit=1").json()
    assert len(p1["data"]) == 1 and p1["meta"]["next_cursor"]
    cur = p1["meta"]["next_cursor"]
    p2 = client.get(f"{H}?metric=power_kw&{RNG}&limit=1&cursor={cur}").json()
    assert [r["event_time"] for r in p2["data"]] == ["2026-10-27T00:02:00Z"] and p2["meta"]["next_cursor"] is None
    # đổi limit/range/metric thì cursor phải bị từ chối; cursor rác cũng vậy.
    for qs in (f"metric=power_kw&{RNG}&limit=2&cursor={cur}",
               f"metric=energy_kwh&{RNG}&limit=1&cursor={cur}",
               "metric=power_kw&start=2026-10-27T00:00:00Z&end=2026-10-27T00:04:00Z&limit=1&cursor=" + cur,
               f"metric=power_kw&{RNG}&cursor=not-a-cursor",
               f"metric=power_kw&{RNG}&cursor=e30"):
        r = client.get(f"{H}?{qs}")
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CURSOR", qs


def test_history_late_and_out_of_order_flags(client, db):
    add_reading(db, message_id="00000000-0000-4000-8000-000000000301", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:03:00Z", received_at="2026-10-27T00:03:01Z", value=1)
    add_reading(db, message_id="00000000-0000-4000-8000-000000000302", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:02:00Z", received_at="2026-10-27T00:03:01Z", value=1)
    add_reading(db, message_id="00000000-0000-4000-8000-000000000303", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:00:00Z", received_at="2026-10-27T00:02:00Z", value=1)      # đúng 120 s
    add_reading(db, message_id="00000000-0000-4000-8000-000000000304", device_id="A-01", metric="power_kw",
                event_time="2026-10-26T23:50:00Z", received_at="2026-10-27T00:03:01Z", value=1)      # trễ nhiều
    db.commit()
    got = {r["message_id"][-3:]: r for r in client.get(
        f"{H}?metric=power_kw&start=2026-10-26T00:00:00Z&end=2026-10-27T01:00:00Z").json()["data"]}
    assert (got["302"]["is_out_of_order"], got["302"]["is_late"]) == (True, False)    # 61 s <= 120 s
    assert (got["303"]["is_late"]) is False                                          # đúng 120 s chưa late
    assert (got["304"]["is_late"], got["304"]["is_out_of_order"]) == (True, True)


def test_history_empty_keeps_query_echo_and_disabled_device_still_queryable(client, db):
    db.execute(text("UPDATE devices SET enabled=false WHERE device_id='A-01'"))
    db.commit()
    r = client.get(f"{H}?metric=power_kw&start=2026-10-26T00:00:00Z&end=2026-10-26T00:01:00Z")
    assert r.status_code == 200 and r.json() == {"data": [], "meta": {
        "generated_at": "2026-10-27T00:03:00Z", "device_id": "A-01", "metric": "power_kw",
        "start": "2026-10-26T00:00:00Z", "end": "2026-10-26T00:01:00Z", "next_cursor": None}}


@pytest.mark.parametrize("path,code,status", [
    ("/api/v1/devices/NOPE/readings?metric=power_kw&" + RNG, "NOT_FOUND", 404),
    ("/api/v1/devices/bad%20id/readings?metric=power_kw&" + RNG, "INVALID_QUERY", 422),
    (H + "?metric=voltage&" + RNG, "INVALID_QUERY", 422),
    (H + "?" + RNG, "INVALID_QUERY", 422),
    (H + "?metric=power_kw&start=2026-10-27T00:03:00Z&end=2026-10-27T00:00:00Z", "INVALID_QUERY", 422),
    (H + "?metric=power_kw&" + RNG + "&limit=0", "INVALID_QUERY", 422),
    (H + "?metric=power_kw&" + RNG + "&limit=1001", "INVALID_QUERY", 422),
    ("/api/v1/devices?building_id=BLD-Z", "NOT_FOUND", 404),
    ("/api/v1/nope", "NOT_FOUND", 404),
    ("/api/v1/alerts?x=1", "INVALID_QUERY", 422),
])
def test_error_envelope(client, path, code, status):
    r = client.get(path, headers={"X-Request-ID": "req-test-01"})
    assert r.status_code == status
    assert r.json() == {"error": {"code": code, "message": r.json()["error"]["message"], "request_id": "req-test-01"}}
    assert r.headers["X-Request-ID"] == "req-test-01"


def test_limit_1000_is_accepted(client, db):
    assert client.get("/api/v1/devices?limit=1000").status_code == 200


def test_alerts_filters_order_and_mismatch(client, db, fixture_data):
    load_fixture(db, fixture_data)
    r = client.get("/api/v1/alerts")
    body = r.json()
    assert r.status_code == 200 and len(body["data"]) == 2
    assert {a["device_id"] for a in body["data"]} == {"A-01"}
    assert [a["detected_at"] for a in body["data"]] == ["2026-10-27T00:02:01Z", "2026-10-27T00:01:01Z"]
    a = body["data"][0]
    assert (a["metric"], a["unit"], a["value"], a["threshold"], a["building_id"]) == ("power_kw", "kW", 12, 10, "BLD-A")
    assert body["meta"] == {"generated_at": "2026-10-27T00:03:00Z", "building_id": None, "device_id": None, "next_cursor": None}
    assert client.get("/api/v1/alerts?building_id=BLD-B").json()["data"] == []
    mm = client.get("/api/v1/alerts?building_id=BLD-B&device_id=A-01")
    assert mm.status_code == 422 and mm.json()["error"]["code"] == "FILTER_MISMATCH"
    p1 = client.get("/api/v1/alerts?limit=1").json()
    p2 = client.get(f"/api/v1/alerts?limit=1&cursor={p1['meta']['next_cursor']}").json()
    assert p1["data"][0]["alert_id"] != p2["data"][0]["alert_id"] and p2["meta"]["next_cursor"] is None


def test_alert_threshold_equal_does_not_alert(client, db):
    add_reading(db, message_id="00000000-0000-4000-8000-000000000401", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:01:00Z", received_at="2026-10-27T00:01:01Z", value=10)
    add_reading(db, message_id="00000000-0000-4000-8000-000000000402", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:02:00Z", received_at="2026-10-27T00:02:01Z", value=10.1)
    db.commit()
    ids = [a["message_id"][-3:] for a in client.get("/api/v1/alerts").json()["data"]]
    assert ids == ["402"]


def test_health_ready_ok(client):
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200 and r.json()["data"] == {"status": "ready"}
