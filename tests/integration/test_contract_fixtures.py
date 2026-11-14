"""Offline fixture/schema checks. These do not test application ingestion."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from qa_contract import REGISTRY, timestamp, validate

ROOT = Path(__file__).resolve().parents[2]


class MQTTFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / 'docs/testing/fixtures/mvp-normal.json').read_text())
        cls.sample = cls.fixture['messages'][0]

    def check(self, payload, topic=None, received_at=None):
        return validate(json.dumps(payload).encode(), topic or self.sample['topic'],
                        received_at or self.sample['received_at'])

    def test_normal_fixture_matches_oracle(self):
        fixture = self.fixture
        unique_ids, unique_readings = set(), set()
        intervals = {}
        totals, duration = {}, {}
        alerts = 0
        start, end = map(timestamp, (fixture['query']['start'], fixture['query']['end']))
        for message in fixture['messages']:
            p = validate(json.dumps(message['payload']).encode(), message['topic'], message['received_at'])
            self.assertNotIn(p['message_id'], unique_ids)
            unique_ids.add(p['message_id'])
            key = (p['device_id'], p['metric'], p['event_time'])
            self.assertNotIn(key, unique_readings)
            unique_readings.add(key)
            if p['metric'] == 'power_kw':
                alerts += p['value'] > 10
                continue
            a, b = timestamp(p['interval_start']), timestamp(p['event_time'])
            for prior_a, prior_b in intervals.setdefault(p['device_id'], []):
                self.assertFalse(a < prior_b and b > prior_a, 'Energy intervals overlap')
            intervals[p['device_id']].append((a, b))
            if start <= a and b <= end:
                building = p['building_id']
                totals[building] = totals.get(building, Decimal(0)) + Decimal(str(p['value']))
                duration[building] = duration.get(building, 0) + (b - a).total_seconds()
        expected = fixture['expected']
        self.assertEqual(len(unique_ids), expected['accepted_readings'])
        self.assertEqual(alerts, expected['alerts'])
        self.assertEqual(set(totals), set(expected['building_energy_kwh']))
        for building, value in expected['building_energy_kwh'].items():
            self.assertEqual(totals[building], Decimal(str(value)))
            device_count = sum(b == building for b in REGISTRY.values())
            ratio = duration[building] / ((end - start).total_seconds() * device_count)
            self.assertAlmostEqual(ratio, expected['coverage_ratio'][building], delta=1e-9)

    def test_invalid_values(self):
        for value in ('12', True, None, -1, float('nan'), float('inf'), 10 ** 400):
            with self.subTest(value_type=type(value).__name__):
                payload = deepcopy(self.sample['payload'])
                payload['value'] = value
                with self.assertRaises(ValueError):
                    self.check(payload)

    def test_schema_and_identifiers(self):
        variants = []
        for key in self.sample['payload']:
            payload = deepcopy(self.sample['payload'])
            del payload[key]
            variants.append(payload)
        for updates in ({'extra': 1}, {'schema_version': '2.0'}, {'metric': 'temperature'},
                        {'device_id': '../A-01'}, {'message_id': 'bad-id'},
                        {'interval_start': '2026-10-27T00:00:00Z'}):
            variants.append({**self.sample['payload'], **updates})
        for payload in variants:
            with self.subTest(keys=sorted(payload)):
                with self.assertRaises(ValueError):
                    self.check(payload)

    def test_timestamp_and_future_boundary(self):
        for value in ('2026-10-27T00:01:00', '2026-10-27T07:01:00+07:00',
                      '2026-02-30T00:00:00Z', '2026-10-27T00:01:00.1234567Z'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check({**self.sample['payload'], 'event_time': value})
        self.check({**self.sample['payload'], 'event_time': '2026-10-27T00:01:06Z'})
        with self.assertRaises(ValueError):
            self.check({**self.sample['payload'], 'event_time': '2026-10-27T00:01:06.000001Z'})

    def test_energy_interval(self):
        payload = {**self.sample['payload'], 'metric': 'energy_kwh',
                   'interval_start': '2026-10-27T00:00:00Z'}
        self.check(payload)
        for interval in (None, '2026-10-27T00:01:00Z', '2026-10-27T00:02:00Z'):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                self.check({**payload, 'interval_start': interval})

    def test_topic_and_registry(self):
        with self.assertRaises(ValueError):
            self.check(self.sample['payload'], topic='campus/v1/BLD-B/A-01/readings')
        with self.assertRaises(ValueError):
            self.check({**self.sample['payload'], 'device_id': 'unknown'},
                       topic='campus/v1/BLD-A/unknown/readings')

    def test_wire_json_and_size(self):
        for raw in (b'{', b'[]', b'null', b'\xff', b'{"value":1,"value":2}', b' ' * 4097):
            with self.subTest(raw_length=len(raw)), self.assertRaises(ValueError):
                validate(raw, self.sample['topic'], self.sample['received_at'])

    def test_duplicate_json_key_in_otherwise_valid_payload(self):
        raw = json.dumps(self.sample['payload']).encode()[:-1] + b',"value":99}'
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            validate(raw, self.sample['topic'], self.sample['received_at'])

    def test_zero_and_payload_size_boundary(self):
        self.check({**self.sample['payload'], 'value': 0})
        raw = json.dumps(self.sample['payload']).encode()
        raw = raw + b' ' * (4096 - len(raw))
        validate(raw, self.sample['topic'], self.sample['received_at'])
        with self.assertRaisesRegex(ValueError, 'PAYLOAD_TOO_LARGE'):
            validate(raw + b' ', self.sample['topic'], self.sample['received_at'])


if __name__ == '__main__':
    unittest.main()
