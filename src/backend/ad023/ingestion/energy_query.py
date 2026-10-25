"""Ingestion-owned read adapter. The only code that knows the layout of
sensor_readings and the SQL form of the window rule."""

import sqlite3

from ad023.core.ports import EnergyTotal, ReadingView, Window

_ENERGY_IN_WINDOW = "metric = 'energy_kwh' AND event_time >= ? AND event_time < ?"


class SqliteEnergyQuery:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def building_energy(self, building_id, window: Window) -> EnergyTotal:
        total, count = self.conn.execute(
            f"SELECT SUM(value), COUNT(*) FROM sensor_readings"
            f" WHERE building_id = ? AND {_ENERGY_IN_WINDOW}",
            (building_id, window.start, window.end)).fetchone()
        return EnergyTotal(total or 0.0, count)

    def energy_by_building(self, window: Window) -> dict:
        rows = self.conn.execute(
            f"SELECT building_id, SUM(value), COUNT(*) FROM sensor_readings"
            f" WHERE {_ENERGY_IN_WINDOW} GROUP BY building_id ORDER BY building_id",
            (window.start, window.end)).fetchall()
        return {b: EnergyTotal(total or 0.0, count) for b, total, count in rows}

    def device_readings(self, device_id, window: Window) -> list:
        rows = self.conn.execute(
            "SELECT event_time, received_at, metric, value FROM sensor_readings"
            " WHERE device_id = ? AND event_time >= ? AND event_time < ?"
            " ORDER BY event_time, reading_id",
            (device_id, window.start, window.end)).fetchall()
        return [ReadingView(*row) for row in rows]

    def device_building(self, device_id):
        row = self.conn.execute("SELECT building_id FROM devices WHERE device_id = ?",
                                (device_id,)).fetchone()
        return row[0] if row else None
