"""Additional week-3 tests; run alongside the Backend branch's real fixtures.

The disposable app05_test database is rebuilt by the target's conftest.
No MQTT ingestion claims are made by these API/DB tests.
"""
import json
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text

from app.models import Building, Device
from app.seed import apply_seed, load_registry
from conftest import BACKEND, SEED_FILE
from loader import load_fixture


def migration_config(database_url, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', database_url)
    cfg = Config(str(BACKEND / 'alembic.ini'))
    cfg.set_main_option('script_location', str(BACKEND / 'alembic'))
    return cfg


def test_ngoc_migration_roundtrip(engine, database_url, monkeypatch):
    # Only the separate db-test container is allowed to lose its test schema.
    assert database_url.rsplit('/', 1)[-1] == 'app05_test'
    assert '@db-test:' in database_url
    cfg = migration_config(database_url, monkeypatch)
    try:
        command.downgrade(cfg, 'base')
        assert not {'buildings', 'devices', 'readings', 'alerts'} & set(inspect(engine).get_table_names())
    finally:
        command.upgrade(cfg, 'head')
    assert {'buildings', 'devices', 'readings', 'alerts'} <= set(inspect(engine).get_table_names())
    command.upgrade(cfg, 'head')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0001'


def test_ngoc_seed_idempotent_preserves_readings(db, fixture_data):
    load_fixture(db, fixture_data)
    before = db.execute(text('SELECT count(*) FROM readings')).scalar_one()
    original_buildings = list(db.scalars(select(Building.building_id).order_by(Building.building_id)))
    original_devices = list(db.scalars(select(Device.device_id).order_by(Device.device_id)))
    for _ in range(2):
        result = apply_seed(db, load_registry(SEED_FILE))
        assert not result['inserted'] and not result['updated']
    assert db.execute(text('SELECT count(*) FROM readings')).scalar_one() == before
    assert list(db.scalars(select(Building.building_id).order_by(Building.building_id))) == original_buildings
    assert list(db.scalars(select(Device.device_id).order_by(Device.device_id))) == original_devices


def test_ngoc_required_indexes(engine):
    expected = {
        'devices': ('building_id',),
        'readings': ('device_id', 'metric', 'event_time', 'message_id'),
        'alerts': ('detected_at', 'alert_id'),
    }
    inspector = inspect(engine)
    for table, columns in expected.items():
        actual = [tuple(index['column_names']) for index in inspector.get_indexes(table)]
        assert columns in actual, (table, columns, actual)


def test_ngoc_history_query_plan(db, fixture_data):
    load_fixture(db, fixture_data)
    query = """SELECT message_id, event_time, value FROM readings
        WHERE device_id = 'A-01' AND metric = 'power_kw'
          AND event_time >= '2026-10-27T00:00:00Z'
          AND event_time < '2026-10-27T00:03:00Z'
        ORDER BY event_time, message_id LIMIT 101"""
    actual = db.execute(text(query)).all()
    assert len(actual) == 2
    assert [row.event_time for row in actual] == sorted(row.event_time for row in actual)
    plan = db.execute(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + query)).scalar_one()
    assert plan[0]['Plan']['Actual Rows'] == 2
    print('QA query plan (small fixture; not a load benchmark):', plan)
    report_dir = os.environ.get('QA_REPORT_DIR')
    if report_dir:
        Path(report_dir, 'history-query-plan.json').write_text(json.dumps(plan, indent=2))
    # PostgreSQL may correctly prefer a sequential scan for 12 rows. Do not force
    # enable_seqscan=off or claim a performance SLA from this sample.


def test_ngoc_api_empty_history(client):
    response = client.get('/api/v1/devices/A-01/readings', params={
        'metric': 'power_kw', 'start': '2026-10-27T00:00:00Z', 'end': '2026-10-27T00:03:00Z'})
    assert response.status_code == 200
    body = response.json()
    assert body['data'] == []
    assert body['meta']['device_id'] == 'A-01'
    assert body['meta']['next_cursor'] is None


def test_ngoc_api_time_order_and_pagination(client, db, fixture_data):
    # Load out of arrival order to ensure API orders by event_time.
    fixture_data['messages'] = list(reversed(fixture_data['messages']))
    load_fixture(db, fixture_data)
    query = {'metric': 'power_kw', 'start': '2026-10-27T00:00:00Z',
             'end': '2026-10-27T00:03:00Z', 'limit': 1}
    first = client.get('/api/v1/devices/A-01/readings', params=query)
    assert first.status_code == 200
    page = first.json()
    assert len(page['data']) == 1 and page['meta']['next_cursor']
    second = client.get('/api/v1/devices/A-01/readings', params={
        **query, 'cursor': page['meta']['next_cursor']})
    assert second.status_code == 200
    last = second.json()
    assert len(last['data']) == 1 and last['meta']['next_cursor'] is None
    rows = page['data'] + last['data']
    assert rows[0]['event_time'] < rows[1]['event_time']
    assert len({row['message_id'] for row in rows}) == 2
    assert all(row['device_id'] == 'A-01' and row['building_id'] == 'BLD-A' for row in rows)


def test_ngoc_api_rejects_unknown_query_parameter(client):
    response = client.get('/api/v1/devices', params={'unexpected': 'x'})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'INVALID_QUERY'
