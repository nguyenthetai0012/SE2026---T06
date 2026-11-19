"""Simulator CLI -> Mosquitto -> worker -> PostgreSQL -> real API application."""
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import text

from test_worker_live_mqtt import broker, worker, wait_for  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]


def test_simulator_through_broker_worker_db_and_api(worker, broker, engine, client):
    worker.start()
    env = {**os.environ, 'MQTT_HOST': '127.0.0.1', 'MQTT_PORT': str(broker)}
    cases = [
        ('normal', '2020-01-01T00:00:00Z', 1),
        ('duplicate', '2020-01-01T00:10:00Z', 1),
        ('invalid', '2020-01-01T00:20:00Z', 1),
        ('late', '2020-01-01T02:00:00Z', 1),
        ('out-of-order', '2020-01-01T03:00:00Z', 2),
    ]
    for mode, start, cycles in cases:
        result = subprocess.run(
            [sys.executable, '-m', 'src.simulator.simulator', '--mode', mode,
             '--cycles', str(cycles), '--devices', '1', '--seed', '42', '--start', start],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=85, check=True,
        )
        assert 'publish_attempts=' in result.stdout
        if mode == 'duplicate':
            assert 'logical_messages=2 publish_attempts=4' in result.stdout
    assert wait_for(engine, 'select count(*) from readings', 10, timeout=15) == 10
    log = worker.stop()
    assert "'duplicate': 2" in log
    assert 'reject MISSING_FIELD' in log and 'reject INVALID_VALUE' in log
    with engine.connect() as connection:
        rows = connection.execute(text("select event_time, is_late, is_out_of_order from readings where metric='power_kw' order by event_time")).all()
    assert len(rows) == 5 and all(row.is_late for row in rows)
    assert rows[-2].is_out_of_order and not rows[-1].is_out_of_order
    response = client.get('/api/v1/devices/A-01/readings', params={
        'metric': 'power_kw', 'start': '2020-01-01T00:00:00Z', 'end': '2020-01-01T04:00:00Z', 'limit': 100,
    })
    assert response.status_code == 200
    items = response.json()['data']
    assert len(items) == 5
    assert all(item['device_id'] == 'A-01' and item['building_id'] == 'BLD-A' and item['is_late'] for item in items)
    assert items[-2]['is_out_of_order'] and not items[-1]['is_out_of_order']
