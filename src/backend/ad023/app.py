"""Composition root: the only place that wires modules together."""

import sqlite3
from types import SimpleNamespace

from ad023.dashboard.service import DashboardService
from ad023.ingestion.energy_query import SqliteEnergyQuery
from ad023.ingestion.store import IngestionStore, init_db
from ad023.reporting.daily_rollup import DailyRollupJob


def build_app(conn=None, clock=None):
    conn = conn or sqlite3.connect(":memory:")
    init_db(conn)
    ingestion = IngestionStore(conn, clock) if clock else IngestionStore(conn)
    energy = SqliteEnergyQuery(conn)
    return SimpleNamespace(
        conn=conn,
        ingestion=ingestion,
        dashboard=DashboardService(energy),
        rollup=DailyRollupJob(energy),
    )
