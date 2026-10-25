-- Owned by the Ingestion module. Other modules must not query these tables.
-- SQLite is used so the prototype runs with the Python standard library only;
-- the team's proposed production store (PR #23) is PostgreSQL and is not validated here.

CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    building_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    reading_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id   TEXT NOT NULL UNIQUE,
    building_id  TEXT NOT NULL,
    device_id    TEXT NOT NULL REFERENCES devices(device_id),
    metric       TEXT NOT NULL,
    value        REAL NOT NULL,
    event_time   TEXT NOT NULL,  -- ISO-8601 UTC, set by the sensor
    received_at  TEXT NOT NULL,  -- ISO-8601 UTC, set by the Backend
    raw_payload  TEXT NOT NULL   -- original JSON, kept for diagnostics only
);

CREATE INDEX IF NOT EXISTS ix_readings_building_metric_time
    ON sensor_readings (building_id, metric, event_time);
CREATE INDEX IF NOT EXISTS ix_readings_device_time
    ON sensor_readings (device_id, event_time);
