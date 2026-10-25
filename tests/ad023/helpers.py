"""Shared fixture for AD-023 tests. Every call to the service goes through
`overview()` / `history()` so that a later signature change touches one place."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "backend"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ad023.app import build_app  # noqa: E402
from ad023.core.auth import Principal  # noqa: E402

DAY13 = ("2026-10-13T00:00:00Z", "2026-10-14T00:00:00Z")
DAY14 = ("2026-10-14T00:00:00Z", "2026-10-15T00:00:00Z")


def ingest(app, message_id, building, device, metric, value, event_time, received_at=None):
    app.ingestion.clock = lambda: received_at or event_time
    return app.ingestion.ingest({
        "schema_version": "1.0", "message_id": message_id, "building_id": building,
        "device_id": device, "event_time": event_time, "metric": metric, "value": value,
    })


def seeded_app():
    app = build_app()
    for device, building in (("METER-01", "BLD-A"), ("METER-02", "BLD-A"), ("METER-03", "BLD-B")):
        app.ingestion.register_device(device, building)
    # Out of order on purpose: 08:15 arrives (late) before 08:00.
    ingest(app, "m-02", "BLD-A", "METER-01", "energy_kwh", 2.25,
           "2026-10-13T08:15:00Z", received_at="2026-10-13T09:00:00Z")
    ingest(app, "m-01", "BLD-A", "METER-01", "energy_kwh", 1.5, "2026-10-13T08:00:00Z")
    ingest(app, "m-03", "BLD-A", "METER-02", "energy_kwh", 0.75, "2026-10-13T08:30:00Z")
    ingest(app, "m-04", "BLD-A", "METER-02", "power_kw", 45.5, "2026-10-13T08:30:00Z")
    ingest(app, "m-05", "BLD-A", "METER-01", "energy_kwh", 4.0, "2026-10-12T23:59:59Z")
    ingest(app, "m-06", "BLD-A", "METER-01", "energy_kwh", 7.0, "2026-10-14T00:00:00Z")
    ingest(app, "m-07", "BLD-B", "METER-03", "energy_kwh", 3.0, "2026-10-13T10:00:00Z")
    return app


# BEHAVIOR-CHANGE-C4: the service now requires a Principal. Characterization
# tests act as a user scoped to every seeded building, so their expectations
# are unchanged; access control itself is tested in test_security.py.
ALL_BUILDINGS = Principal("tester-all", frozenset({"BLD-A", "BLD-B"}))


# --- the only two call sites of the Dashboard service -----------------------
def overview(app, building_id, window, principal=ALL_BUILDINGS):
    return app.dashboard.get_building_overview(principal, building_id, *window)


def history(app, device_id, window, principal=ALL_BUILDINGS):
    return app.dashboard.get_device_history(principal, device_id, *window)
