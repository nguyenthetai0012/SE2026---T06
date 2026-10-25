"""Ingestion module: validates readings and owns the sensor_readings table."""

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

UNITS = {"power_kw": "kW", "energy_kwh": "kWh"}
REQUIRED = ("schema_version", "message_id", "building_id", "device_id",
            "event_time", "metric", "value")
SCHEMA = Path(__file__).with_name("schema.sql")


class InvalidReading(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text):
    """Accept only 'YYYY-MM-DDTHH:MM:SSZ' so string order equals time order."""
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as exc:
        raise InvalidReading(f"event_time must be ISO-8601 UTC: {text!r}") from exc
    return text


def init_db(conn):
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))


class IngestionStore:
    def __init__(self, conn: sqlite3.Connection, clock=utc_now):
        self.conn = conn
        self.clock = clock

    def register_device(self, device_id, building_id):
        self.conn.execute("INSERT OR REPLACE INTO devices VALUES (?, ?)",
                          (device_id, building_id))

    def ingest(self, payload: dict) -> str:
        """Return 'accepted' or 'duplicate'; raise InvalidReading otherwise."""
        missing = [k for k in REQUIRED if k not in payload]
        if missing:
            raise InvalidReading(f"missing fields: {missing}")
        if payload["metric"] not in UNITS:
            raise InvalidReading(f"unknown metric: {payload['metric']}")
        value = payload["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise InvalidReading("value must be a finite number")
        event_time = parse_utc(payload["event_time"])
        row = self.conn.execute("SELECT building_id FROM devices WHERE device_id = ?",
                                (payload["device_id"],)).fetchone()
        if row is None or row[0] != payload["building_id"]:
            raise InvalidReading("device not registered for this building")
        try:
            self.conn.execute(
                "INSERT INTO sensor_readings (message_id, building_id, device_id, metric,"
                " value, event_time, received_at, raw_payload) VALUES (?,?,?,?,?,?,?,?)",
                (payload["message_id"], payload["building_id"], payload["device_id"],
                 payload["metric"], float(value), event_time, self.clock(),
                 json.dumps(payload, sort_keys=True)))
        except sqlite3.IntegrityError:
            return "duplicate"
        return "accepted"
