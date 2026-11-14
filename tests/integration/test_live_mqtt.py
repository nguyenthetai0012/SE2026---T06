"""Real MQTT -> worker -> PostgreSQL tests, opt-in and fail closed.

Requires a running real worker using app05-ngoc-qa's db and mqtt services.
No loader or fake consumer is supplied by QA. Uses only dedicated QA data.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/scripts'))
from dev import compose, require_env


def sql(query):
    result = compose('exec', '-T', 'db', 'psql', '-XAt', '-v', 'ON_ERROR_STOP=1',
                     '-U', 'app05_qa', '-d', 'app05_qa', '-c', query, capture=True)
    return result.stdout.strip()


def payload(value=12):
    return {'schema_version': '1.0', 'message_id': str(uuid.uuid4()),
            'building_id': 'BLD-A', 'device_id': 'A-01', 'metric': 'power_kw',
            'event_time': (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat().replace('+00:00', 'Z'),
            'value': value}


def publish(messages):
    compose('exec', '-T', 'mqtt', 'mosquitto_pub', '-h', 'localhost',
            '-V', 'mqttv311', '-q', '1', '-t', 'campus/v1/BLD-A/A-01/readings',
            '-l', input_text=''.join(json.dumps(p) + '\n' for p in messages), capture=True)


def row(message_id):
    # IDs only come from uuid4 in this module; never interpolate external input.
    uuid.UUID(message_id)
    value = sql("SELECT row_to_json(r)::text FROM readings r WHERE message_id='" + message_id + "'")
    return json.loads(value) if value else None


def wait_for(message_id):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = row(message_id)
        if result is not None:
            return result
        time.sleep(0.1)
    raise AssertionError('Worker chưa lưu reading trong cửa sổ kiểm tra 15s (không phải SLA).')


class LiveMQTTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('QA_MQTT_WORKER_READY') != '1':
            raise RuntimeError('BLOCKED: cần worker thật; chỉ đặt QA_MQTT_WORKER_READY=1 sau khi worker đã chạy.')
        require_env()
        tables = sql("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' "
                     "AND table_name IN ('readings','devices','alerts')")
        if tables != '3':
            raise RuntimeError('BLOCKED: chưa có migration/schema Backend trong DB QA.')
        seed = sql("SELECT count(*) FROM devices WHERE device_id='A-01' AND building_id='BLD-A' "
                   "AND enabled AND period_seconds=60 AND power_threshold_kw=10")
        if seed != '1':
            raise RuntimeError('BLOCKED: seed QA A-01 không khớp baseline.')

    def accepted(self):
        original = payload()
        publish([original])
        return original, wait_for(original['message_id'])

    def assert_one_alert(self, message_id):
        self.assertEqual(sql("SELECT count(*) FROM alerts WHERE message_id='" + message_id + "'"), '1')

    def test_normal_power_ingestion(self):
        original, stored = self.accepted()
        self.assertEqual(stored['device_id'], original['device_id'])
        self.assertEqual(float(stored['value']), original['value'])
        self.assert_one_alert(original['message_id'])

    def test_replay_duplicate_preserves_reading_and_alert(self):
        original, stored = self.accepted()
        barrier = payload(0)
        # Same MQTT connection/topic: one MVP worker processes the barrier after replay.
        publish([original, original, barrier])
        wait_for(barrier['message_id'])
        self.assertEqual(row(original['message_id']), stored)
        self.assertEqual(sql("SELECT count(*) FROM readings WHERE message_id='" + original['message_id'] + "'"), '1')
        self.assert_one_alert(original['message_id'])

    def test_reordered_json_keys_are_duplicate(self):
        original, stored = self.accepted()
        reordered = dict(reversed(list(original.items())))
        barrier = payload(0)
        publish([reordered, barrier])
        wait_for(barrier['message_id'])
        self.assertEqual(row(original['message_id']), stored)
        self.assert_one_alert(original['message_id'])

    def test_conflicting_message_id_does_not_overwrite(self):
        original, stored = self.accepted()
        barrier = payload(0)
        publish([{**original, 'value': 99}, barrier])
        wait_for(barrier['message_id'])
        self.assertEqual(row(original['message_id']), stored)
        self.assert_one_alert(original['message_id'])

    def test_invalid_value_not_persisted(self):
        invalid = payload('12')
        barrier = payload(0)
        publish([invalid, barrier])
        wait_for(barrier['message_id'])
        self.assertIsNone(row(invalid['message_id']))
        self.assertEqual(sql("SELECT count(*) FROM alerts WHERE message_id='" + invalid['message_id'] + "'"), '0')


if __name__ == '__main__':
    unittest.main()
