"""Dashboard module (BASELINE C1 — contains deliberate design problems).

Problems kept on purpose for the AD-023 analysis:
  P1  Dashboard reads the Ingestion-owned table with raw SQL (boundary / ownership).
  P2  Energy aggregation SQL and the window rule are duplicated in DailyRollupJob.
  P3  No authorization check and raw payloads are returned to the caller.
"""

import sqlite3
from datetime import datetime

UNITS = {"power_kw": "kW", "energy_kwh": "kWh"}  # duplicated from ingestion
LATE_AFTER_SECONDS = 300  # [ĐỀ XUẤT] from MQTT draft PR #10, not approved


def _seconds_between(earlier, later):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(later, fmt) - datetime.strptime(earlier, fmt)).total_seconds()


class DashboardService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_building_overview(self, building_id, start, end):
        total, count = self.conn.execute(
            "SELECT SUM(value), COUNT(*) FROM sensor_readings"
            " WHERE building_id = ? AND metric = 'energy_kwh'"
            " AND event_time >= ? AND event_time < ?",
            (building_id, start, end)).fetchone()
        debug = [r[0] for r in self.conn.execute(
            "SELECT raw_payload FROM sensor_readings WHERE building_id = ?"
            " ORDER BY received_at DESC, reading_id DESC LIMIT 5", (building_id,))]
        return {
            "building_id": building_id,
            "metric": "energy_kwh",
            "unit": UNITS["energy_kwh"],
            "window": {"start": start, "end": end},
            "value": round(total or 0.0, 3),
            "reading_count": count,
            "raw_debug_records": debug,
        }

    def get_device_history(self, device_id, start, end):
        rows = self.conn.execute(
            "SELECT event_time, received_at, metric, value FROM sensor_readings"
            " WHERE device_id = ? AND event_time >= ? AND event_time < ?"
            " ORDER BY event_time, reading_id",
            (device_id, start, end)).fetchall()
        return [{
            "event_time": event_time,
            "received_at": received_at,
            "metric": metric,
            "value": value,
            "unit": UNITS[metric],
            "late": _seconds_between(event_time, received_at) > LATE_AFTER_SECONDS,
        } for event_time, received_at, metric, value in rows]
