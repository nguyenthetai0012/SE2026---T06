"""Reporting module (BASELINE C1): daily energy totals per building.

Duplicates the aggregation SQL and window rule of DashboardService (problem P2)
and reads the Ingestion-owned table directly (problem P1).
"""

import sqlite3
from datetime import date, timedelta


class DailyRollupJob:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def run(self, day: date):
        start = f"{day.isoformat()}T00:00:00Z"
        end = f"{(day + timedelta(days=1)).isoformat()}T00:00:00Z"
        rows = self.conn.execute(
            "SELECT building_id, SUM(value) FROM sensor_readings"
            " WHERE metric = 'energy_kwh' AND event_time >= ? AND event_time < ?"
            " GROUP BY building_id ORDER BY building_id",
            (start, end)).fetchall()
        return {building_id: round(total or 0.0, 3) for building_id, total in rows}
