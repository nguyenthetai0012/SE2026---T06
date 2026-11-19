import json
from datetime import datetime, timedelta, timezone
import unittest

from src.simulator.simulator import DEFAULT_REGISTRY, generate, read_registry


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.devices = read_registry(DEFAULT_REGISTRY)
        self.start = datetime(2026, 10, 27, tzinfo=timezone.utc)

    def batches(self, mode, cycles=5):
        return list(generate(self.devices, mode, 42, self.start, cycles))

    def test_normal_is_deterministic_and_energy_matches_power(self):
        batches = self.batches('normal', 2)
        self.assertEqual(batches, self.batches('normal', 2))
        self.assertEqual(len(batches[0]), 6)
        for i in range(0, 6, 2):
            topic, power, _ = batches[0][i]
            _, energy, _ = batches[0][i + 1]
            a, b = json.loads(power), json.loads(energy)
            self.assertEqual(topic, f"campus/v1/{a['building_id']}/{a['device_id']}/readings")
            self.assertNotIn('interval_start', a)
            self.assertEqual(b['interval_start'], '2026-10-27T00:00:00Z')
            self.assertAlmostEqual(b['value'], a['value'] / 60, places=8)
            self.assertNotEqual(a['message_id'], b['message_id'])

    def test_duplicate_preserves_bytes_and_id(self):
        batch = self.batches('duplicate', 1)[0]
        for i in range(0, len(batch), 2):
            self.assertEqual(batch[i][:2], batch[i + 1][:2])
            self.assertTrue(batch[i][2])
            self.assertFalse(batch[i + 1][2])

    def test_invalid_late_and_out_of_order(self):
        invalid = self.batches('invalid', 1)[0]
        self.assertNotIn('value', json.loads(invalid[0][1]))
        self.assertIsInstance(json.loads(invalid[1][1])['value'], str)
        self.assertGreater(len(invalid[5][1]), 4096)
        late = json.loads(self.batches('late', 1)[0][0][1])
        self.assertEqual(late['event_time'], '2026-10-26T23:01:00Z')
        batches = self.batches('out-of-order', 2)
        first, second = [json.loads(batch[0][1]) for batch in batches]
        self.assertGreater(first['event_time'], second['event_time'])
        self.assertNotEqual(first['message_id'], second['message_id'])

    def test_offline_stops_both_metrics_then_resumes(self):
        batches = self.batches('offline')
        ids = [[json.loads(item[1])['device_id'] for item in batch] for batch in batches]
        self.assertEqual(ids[0].count('A-02'), 2)
        self.assertTrue(all('A-02' not in ids[i] and len(ids[i]) == 4 for i in (1, 2, 3)))
        self.assertEqual(ids[4].count('A-02'), 2)
        self.assertEqual(self.start + timedelta(minutes=5), datetime(2026, 10, 27, 0, 5, tzinfo=timezone.utc))

    def test_reject_insufficient_offline_cycles(self):
        with self.assertRaises(ValueError):
            self.batches('offline', 4)


if __name__ == '__main__':
    unittest.main()
