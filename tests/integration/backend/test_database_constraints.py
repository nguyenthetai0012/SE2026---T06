"""Bất biến phải được giữ ở DB (không chỉ ở worker): xem docs/architecture/mvp-system.md."""
from __future__ import annotations

import pytest
from loader import add_reading, load_fixture
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import Alert, Device, Reading
from app.seed import SeedError, apply_seed, load_registry
from conftest import SEED_FILE


def _energy(db, mid, start, end, value=0.1, device="A-01"):
    return add_reading(db, message_id=mid, device_id=device, metric="energy_kwh", event_time=f"2026-10-27T{end}Z",
                       received_at=f"2026-10-27T{end}Z", interval_start=f"2026-10-27T{start}Z", value=value)


def test_overlapping_energy_interval_rejected_by_db(db, fixture_data):
    load_fixture(db, fixture_data)
    with pytest.raises(IntegrityError) as e:
        _energy(db, "00000000-0000-4000-8000-000000000501", "00:00:30", "00:01:30")
    assert "ex_readings_energy_no_overlap" in str(e.value)
    db.rollback()


def test_adjacent_intervals_and_other_device_are_allowed(db):
    _energy(db, "00000000-0000-4000-8000-000000000511", "00:00:00", "00:01:00")
    _energy(db, "00000000-0000-4000-8000-000000000512", "00:01:00", "00:02:00")        # giáp biên
    _energy(db, "00000000-0000-4000-8000-000000000513", "00:00:30", "00:01:30", device="A-02")   # device khác
    db.commit()


def test_same_event_time_conflicts(db):
    add_reading(db, message_id="00000000-0000-4000-8000-000000000521", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:01:00Z", received_at="2026-10-27T00:01:01Z", value=1)
    db.commit()
    with pytest.raises(IntegrityError) as e:
        add_reading(db, message_id="00000000-0000-4000-8000-000000000522", device_id="A-01", metric="power_kw",
                    event_time="2026-10-27T00:01:00Z", received_at="2026-10-27T00:01:02Z", value=2)
    assert "uq_readings_device_metric_event" in str(e.value)
    db.rollback()


@pytest.mark.parametrize("kwargs,constraint", [
    (dict(metric="power_kw", value=-1), "ck_readings_value_nonneg"),
    (dict(metric="voltage", value=1), "ck_readings_metric"),
    (dict(metric="power_kw", value=1, interval_start="2026-10-27T00:00:00Z"), "ck_readings_interval_iff_energy"),
    (dict(metric="energy_kwh", value=1), "ck_readings_interval_iff_energy"),
    (dict(metric="energy_kwh", value=1, interval_start="2026-10-27T00:01:00Z"), "ck_readings_interval_before_event"),
])
def test_reading_check_constraints(db, kwargs, constraint):
    with pytest.raises(IntegrityError) as e:
        add_reading(db, message_id="00000000-0000-4000-8000-000000000531", device_id="A-01",
                    event_time="2026-10-27T00:01:00Z", received_at="2026-10-27T00:01:01Z", **kwargs)
    assert constraint in str(e.value)
    db.rollback()


def test_unknown_device_and_bad_ids_rejected(db):
    with pytest.raises(IntegrityError):
        db.add(Reading(message_id="00000000-0000-4000-8000-000000000541", device_id="NOPE", metric="power_kw",
                       event_time=__import__("loader").utc("2026-10-27T00:01:00Z"),
                       received_at=__import__("loader").utc("2026-10-27T00:01:01Z"), value=1,
                       is_late=False, is_out_of_order=False, period_seconds=60))
        db.flush()
    db.rollback()
    with pytest.raises(IntegrityError) as e:
        db.execute(text("INSERT INTO devices(device_id,building_id,name,period_seconds,power_threshold_kw) "
                        "VALUES ('bad id','BLD-A','x',60,10)"))
    assert "ck_devices_id_format" in str(e.value)
    db.rollback()


def test_alert_unique_per_message_and_over_threshold_only(db):
    add_reading(db, message_id="00000000-0000-4000-8000-000000000551", device_id="A-01", metric="power_kw",
                event_time="2026-10-27T00:01:00Z", received_at="2026-10-27T00:01:01Z", value=12)
    db.commit()
    dup = Alert(alert_id="dup", message_id="00000000-0000-4000-8000-000000000551", device_id="A-01",
                event_time=__import__("loader").utc("2026-10-27T00:01:00Z"), detected_at=__import__("loader").utc("2026-10-27T00:01:01Z"),
                value_kw=12, threshold_kw=10, description="x")
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    with pytest.raises(IntegrityError) as e:
        db.execute(text("UPDATE alerts SET value_kw = threshold_kw"))
    assert "ck_alerts_over_threshold" in str(e.value)
    db.rollback()


def test_device_checks(db):
    for sql, name in (("UPDATE devices SET period_seconds=0 WHERE device_id='A-01'", "ck_devices_period_positive"),
                      ("UPDATE devices SET power_threshold_kw=-1 WHERE device_id='A-01'", "ck_devices_threshold_nonneg")):
        with pytest.raises(IntegrityError) as e:
            db.execute(text(sql))
        assert name in str(e.value)
        db.rollback()


def test_seed_is_idempotent_and_reports_diff(db):
    data = load_registry(SEED_FILE)
    diff = apply_seed(db, data)
    assert diff["inserted"] == [] and diff["updated"] == [] and len(diff["unchanged"]) == 5
    assert db.query(Device).count() == 3
    data["devices"][0]["name"] = "Renamed"
    diff = apply_seed(db, data)
    assert diff["updated"] == ["device:A-01(name)"]


def test_seed_refuses_to_move_device_with_history(db, fixture_data):
    load_fixture(db, fixture_data)
    data = load_registry(SEED_FILE)
    data["devices"][0]["building_id"] = "BLD-B"
    with pytest.raises(SeedError, match="đã có"):
        apply_seed(db, data)
    db.rollback()


@pytest.mark.parametrize("mutate,msg", [
    (lambda d: d["devices"].append(dict(d["devices"][0])), "trùng device_id"),
    (lambda d: d["devices"][0].update(building_id="BLD-X"), "device không hợp lệ"),
    (lambda d: d["devices"][0].update(period_seconds=0), "period_seconds"),
    (lambda d: d["devices"][0].update(enabled="yes"), "enabled"),
    (lambda d: d["devices"][0].update(power_threshold_kw=-1), "power_threshold_kw"),
    (lambda d: d["devices"][0].update(device_id="bad id"), "device không hợp lệ"),
    (lambda d: d["devices"][0].pop("name"), "thiếu/thừa"),
    (lambda d: d["buildings"].append(dict(d["buildings"][0])), "trùng building_id"),
])
def test_seed_validation(tmp_path, mutate, msg):
    import json
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    mutate(data)
    p = tmp_path / "r.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SeedError, match=msg):
        load_registry(p)
