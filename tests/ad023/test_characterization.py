"""Characterization tests: pin the observable behavior of the baseline (C1)
so that the refactoring in C2/C3 can be shown to preserve it.

Tests tagged BEHAVIOR-CHANGE-C4 describe baseline flaws; C4 changes them on
purpose and must update exactly those tests."""

import unittest
from datetime import date

from tests.ad023.helpers import DAY13, DAY14, history, ingest, overview, seeded_app
from ad023.ingestion.store import InvalidReading


class OverviewBehavior(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_sums_energy_of_building_in_window(self):
        result = overview(self.app, "BLD-A", DAY13)
        self.assertEqual(result["value"], 4.5)          # 2.25 + 1.5 + 0.75
        self.assertEqual(result["reading_count"], 3)
        self.assertEqual(result["unit"], "kWh")
        self.assertEqual(result["metric"], "energy_kwh")
        self.assertEqual(result["window"], {"start": DAY13[0], "end": DAY13[1]})

    def test_window_is_start_inclusive_end_exclusive(self):
        self.assertEqual(overview(self.app, "BLD-A", DAY14)["value"], 7.0)
        self.assertNotIn(7.0, [r["value"] for r in history(self.app, "METER-01", DAY13)])

    def test_power_readings_are_not_counted_as_energy(self):
        self.assertEqual(overview(self.app, "BLD-A", DAY13)["reading_count"], 3)

    def test_empty_window_is_zero_not_error(self):
        result = overview(self.app, "BLD-A", ("2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"))
        self.assertEqual((result["value"], result["reading_count"]), (0.0, 0))

    def test_other_buildings_are_not_mixed_in(self):
        self.assertEqual(overview(self.app, "BLD-B", DAY13)["value"], 3.0)


class HistoryBehavior(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_sorted_by_event_time_even_when_received_out_of_order(self):
        times = [r["event_time"] for r in history(self.app, "METER-01", DAY13)]
        self.assertEqual(times, ["2026-10-13T08:00:00Z", "2026-10-13T08:15:00Z"])

    def test_late_flag_uses_received_at_minus_event_time(self):
        late = {r["event_time"]: r["late"] for r in history(self.app, "METER-01", DAY13)}
        self.assertEqual(late, {"2026-10-13T08:00:00Z": False, "2026-10-13T08:15:00Z": True})

    def test_each_reading_carries_its_unit(self):
        units = {r["metric"]: r["unit"] for r in history(self.app, "METER-02", DAY13)}
        self.assertEqual(units, {"energy_kwh": "kWh", "power_kw": "kW"})


class RollupBehavior(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_daily_totals_per_building(self):
        self.assertEqual(self.app.rollup.run(date(2026, 10, 13)), {"BLD-A": 4.5, "BLD-B": 3.0})

    def test_rollup_agrees_with_dashboard_for_the_same_day(self):
        totals = self.app.rollup.run(date(2026, 10, 13))
        for building in ("BLD-A", "BLD-B"):
            self.assertEqual(totals[building], overview(self.app, building, DAY13)["value"])


class IngestionBehavior(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_duplicate_message_is_counted_once(self):
        status = ingest(self.app, "m-01", "BLD-A", "METER-01", "energy_kwh", 1.5,
                        "2026-10-13T08:00:00Z")
        self.assertEqual(status, "duplicate")
        self.assertEqual(overview(self.app, "BLD-A", DAY13)["value"], 4.5)

    def test_invalid_readings_are_rejected_and_not_counted(self):
        bad = [
            ("x-1", "BLD-A", "METER-99", "energy_kwh", 9.0, "2026-10-13T09:00:00Z"),
            ("x-2", "BLD-B", "METER-01", "energy_kwh", 9.0, "2026-10-13T09:00:00Z"),
            ("x-3", "BLD-A", "METER-01", "energy_kwh", 9.0, "13/10/2026 09:00"),
            ("x-4", "BLD-A", "METER-01", "voltage", 9.0, "2026-10-13T09:00:00Z"),
            ("x-5", "BLD-A", "METER-01", "energy_kwh", float("nan"), "2026-10-13T09:00:00Z"),
        ]
        for args in bad:
            with self.subTest(message_id=args[0]), self.assertRaises(InvalidReading):
                ingest(self.app, *args)
        self.assertEqual(overview(self.app, "BLD-A", DAY13)["value"], 4.5)


class BaselineFlaws(unittest.TestCase):
    """BEHAVIOR-CHANGE-C4: these document flaws P3 of the baseline."""

    def setUp(self):
        self.app = seeded_app()

    def test_overview_leaks_raw_payloads(self):  # BEHAVIOR-CHANGE-C4
        self.assertIn("raw_debug_records", overview(self.app, "BLD-A", DAY13))

    def test_any_caller_can_read_any_building(self):  # BEHAVIOR-CHANGE-C4
        self.assertEqual(overview(self.app, "BLD-B", DAY13)["value"], 3.0)


if __name__ == "__main__":
    unittest.main()
