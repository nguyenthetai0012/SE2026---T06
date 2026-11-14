"""Hợp đồng ORM <-> migration và guard ở tầng DB (risk: mock che giấu contract sai với database)."""
from __future__ import annotations

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from export_helpers import make_client
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import Base

EXPORT_TABLES = {"export_clients", "export_client_scopes", "exports"}


def test_orm_models_match_alembic_schema(engine):
    assert EXPORT_TABLES <= set(Base.metadata.tables), "ORM chưa khai báo bảng export"
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], diff


def _insert_export(db, export_id: str, key: str):
    db.execute(text("""
        INSERT INTO exports (export_id, client_id, idempotency_key, request_hash, building_id, metric,
                             start_at, end_at, row_count, content_sha256, content, created_at)
        VALUES (:id, 'ops', :k, repeat('a', 64), 'BLD-A', 'power_kw', '2026-10-27T00:00:00Z',
                '2026-10-27T00:03:00Z', 0, repeat('b', 64), '\\x', now())"""), {"id": export_id, "k": key})


def test_database_enforces_one_export_per_client_and_key(db):
    db.execute(text("TRUNCATE export_clients RESTART IDENTITY CASCADE"))
    make_client(db, "ops", ["BLD-A"])
    _insert_export(db, "00000000-0000-4000-8000-0000000000a1", "key-db-000001")
    db.commit()
    with pytest.raises(IntegrityError) as e:
        _insert_export(db, "00000000-0000-4000-8000-0000000000a2", "key-db-000001")
    assert "uq_exports_client_key" in str(e.value)
    db.rollback()


@pytest.mark.parametrize("start,end,constraint", [
    ("2026-10-27T00:03:00Z", "2026-10-27T00:00:00Z", "ck_exports_range_order"),
    ("2026-10-01T00:00:00Z", "2026-11-01T00:00:01Z", "ck_exports_range_max_31d"),
])
def test_database_enforces_range(db, start, end, constraint):
    db.execute(text("TRUNCATE export_clients RESTART IDENTITY CASCADE"))
    make_client(db, "ops", ["BLD-A"])
    with pytest.raises(IntegrityError) as e:
        db.execute(text("""
            INSERT INTO exports (export_id, client_id, idempotency_key, request_hash, building_id, metric,
                                 start_at, end_at, row_count, content_sha256, content, created_at)
            VALUES (gen_random_uuid(), 'ops', 'key-range-0001', repeat('a', 64), 'BLD-A', 'power_kw',
                    :s, :e, 0, repeat('b', 64), '\\x', now())"""), {"s": start, "e": end})
    assert constraint in str(e.value)
    db.rollback()
