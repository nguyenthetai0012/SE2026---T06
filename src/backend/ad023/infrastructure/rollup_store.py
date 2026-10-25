"""SQLite adapter for the Reporting-owned rollup tables (daily_rollups,
rollup_quarantine). The CHECK and PRIMARY KEY constraints are the database
half of the rollup invariant; the domain half lives in reporting/batch.py."""

import sqlite3
from datetime import datetime, timezone

from ad023.core.ports import PublishedRollup

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_rollups (
    building_id   TEXT    NOT NULL,
    day           TEXT    NOT NULL,
    run_id        TEXT    NOT NULL,
    total_kwh     REAL    NOT NULL CHECK (total_kwh >= 0),
    reading_count INTEGER NOT NULL CHECK (reading_count >= 0),
    computed_at   TEXT    NOT NULL,
    PRIMARY KEY (building_id, day)          -- at most one published value per partition
);
CREATE TABLE IF NOT EXISTS rollup_quarantine (
    building_id    TEXT NOT NULL,
    day            TEXT NOT NULL,
    run_id         TEXT NOT NULL,
    error          TEXT NOT NULL,
    quarantined_at TEXT NOT NULL,
    PRIMARY KEY (building_id, day)
);
"""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SqliteRollupStore:
    def __init__(self, conn: sqlite3.Connection, clock=_now):
        self.conn = conn
        self.clock = clock
        conn.executescript(SCHEMA)

    def publish(self, building_id, day, run_id, total_kwh, reading_count):
        with self.conn:  # one transaction per partition
            self.conn.execute(
                "INSERT INTO daily_rollups VALUES (?,?,?,?,?,?)"
                " ON CONFLICT (building_id, day) DO UPDATE SET run_id = excluded.run_id,"
                " total_kwh = excluded.total_kwh, reading_count = excluded.reading_count,"
                " computed_at = excluded.computed_at",
                (building_id, day, run_id, total_kwh, reading_count, self.clock()))
            self.conn.execute("DELETE FROM rollup_quarantine WHERE building_id = ? AND day = ?",
                              (building_id, day))

    def quarantine(self, building_id, day, run_id, error):
        # Never touches daily_rollups: the last good value stays published.
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO rollup_quarantine VALUES (?,?,?,?,?)",
                (building_id, day, run_id, error[:500], self.clock()))

    def published(self, day):
        rows = self.conn.execute(
            "SELECT building_id, day, run_id, total_kwh, reading_count FROM daily_rollups"
            " WHERE day = ? ORDER BY building_id", (day,))
        return {r[0]: PublishedRollup(*r) for r in rows}

    def quarantined(self, day):
        rows = self.conn.execute(
            "SELECT building_id, error FROM rollup_quarantine WHERE day = ? ORDER BY building_id",
            (day,))
        return dict(rows.fetchall())
