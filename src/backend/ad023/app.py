"""Composition root: the only place that wires modules together."""

import sqlite3
from datetime import date
from types import SimpleNamespace

from ad023.core.auth import AuditLog, ScopeAuthPolicy
from ad023.dashboard.service import DashboardService
from ad023.infrastructure.rollup_store import SqliteRollupStore
from ad023.ingestion.energy_query import SqliteEnergyQuery
from ad023.ingestion.store import IngestionStore, init_db
from ad023.reporting.batch import RollupBatch
from ad023.reporting.daily_rollup import DailyRollupJob


def build_app(conn=None, clock=None, auth=None, today=date.today, transform=None):
    conn = conn or sqlite3.connect(":memory:")
    init_db(conn)
    ingestion = IngestionStore(conn, clock) if clock else IngestionStore(conn)
    energy = SqliteEnergyQuery(conn)
    audit = AuditLog()
    rollup_store = SqliteRollupStore(conn)
    return SimpleNamespace(
        conn=conn,
        ingestion=ingestion,
        audit=audit,
        dashboard=DashboardService(energy, auth or ScopeAuthPolicy(), audit),
        rollup=DailyRollupJob(energy),
        rollup_store=rollup_store,
        batch=(RollupBatch(energy, rollup_store, today, transform) if transform
               else RollupBatch(energy, rollup_store, today)),
    )
