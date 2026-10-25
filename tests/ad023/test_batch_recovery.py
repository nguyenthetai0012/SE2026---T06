"""AD-023 architecture incident: a batch job processes part of the data wrongly;
the system must isolate the fault and recover without re-running everything."""

import sqlite3
import unittest
from datetime import date

from tests.ad023.helpers import DAY13, ingest, overview, seeded_app
from ad023.reporting.batch import RetentionExceeded, RollupBatch

DAY = date(2026, 10, 13)
TODAY = date(2026, 10, 25)


def buggy(building_id, kwh):
    """A faulty release: silently wrong for BLD-B, crashes for BLD-C."""
    if building_id == "BLD-B":
        return kwh * 1000          # e.g. Wh/kWh unit bug: silent, wrong value
    if building_id == "BLD-C":
        raise ArithmeticError("corrupt partition")
    return kwh


class CountingEnergy:
    """Spy around the real port: records which partitions were (re)computed."""

    def __init__(self, inner):
        self.inner, self.computed = inner, []

    def building_energy(self, building_id, window):
        self.computed.append(building_id)
        return self.inner.building_energy(building_id, window)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def app_with_three_buildings():
    app = seeded_app()
    app.ingestion.register_device("METER-05", "BLD-C")
    ingest(app, "m-08", "BLD-C", "METER-05", "energy_kwh", 1.25, "2026-10-13T12:00:00Z")
    return app


def batch(app, transform=None, energy=None):
    energy = energy or app.batch.energy
    if transform:
        return RollupBatch(energy, app.rollup_store, lambda: TODAY, transform)
    return RollupBatch(energy, app.rollup_store, lambda: TODAY)


class FaultIsolation(unittest.TestCase):
    def setUp(self):
        self.app = app_with_three_buildings()

    def test_healthy_run_publishes_every_partition_and_reconciles(self):
        b = batch(self.app)
        report = b.execute(DAY)
        self.assertEqual(report.published, ["BLD-A", "BLD-B", "BLD-C"])
        totals = {k: v.total_kwh for k, v in self.app.rollup_store.published("2026-10-13").items()}
        self.assertEqual(totals, {"BLD-A": 4.5, "BLD-B": 3.0, "BLD-C": 1.25})
        self.assertEqual(totals["BLD-A"], overview(self.app, "BLD-A", DAY13)["value"])
        self.assertEqual(b.reconcile(DAY), [])

    def test_crashing_partition_is_quarantined_and_others_still_publish(self):
        report = batch(self.app, buggy).execute(DAY)
        self.assertEqual(report.published, ["BLD-A", "BLD-B"])
        self.assertEqual(report.quarantined, {"BLD-C": "ArithmeticError"})
        self.assertIn("BLD-C", self.app.rollup_store.quarantined("2026-10-13"))
        self.assertEqual(self.app.rollup_store.published("2026-10-13")["BLD-A"].total_kwh, 4.5)

    def test_quarantine_keeps_last_good_value(self):
        good = batch(self.app).execute(DAY)
        batch(self.app, buggy).execute(DAY)
        row = self.app.rollup_store.published("2026-10-13")["BLD-C"]
        self.assertEqual((row.total_kwh, row.run_id), (1.25, good.run_id))

    def test_invariant_violation_in_domain_is_quarantined(self):
        report = batch(self.app, lambda b, kwh: -1.0 if b == "BLD-A" else kwh).execute(DAY)
        self.assertEqual(report.quarantined, {"BLD-A": "RollupInvariantError"})
        self.assertNotIn("BLD-A", self.app.rollup_store.published("2026-10-13"))

    def test_database_rejects_negative_total_even_if_domain_check_is_bypassed(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.app.rollup_store.publish("BLD-A", "2026-10-13", "manual", -5.0, 1)


class PartialRecovery(unittest.TestCase):
    def setUp(self):
        self.app = app_with_three_buildings()
        self.first = batch(self.app, buggy).execute(DAY)

    def test_reconcile_detects_silent_and_crashed_partitions(self):
        self.assertEqual(batch(self.app).reconcile(DAY), ["BLD-B", "BLD-C"])

    def test_recover_reruns_only_bad_partitions(self):
        spy = CountingEnergy(self.app.batch.energy)
        fixed = batch(self.app, energy=spy)
        bad = fixed.reconcile(DAY)
        spy.computed.clear()
        report = fixed.recover(DAY, bad)
        self.assertEqual(spy.computed, ["BLD-B", "BLD-C"])          # BLD-A not recomputed
        self.assertEqual(report.published, ["BLD-B", "BLD-C"])
        rows = self.app.rollup_store.published("2026-10-13")
        self.assertEqual(rows["BLD-A"].run_id, self.first.run_id)    # untouched
        self.assertEqual({k: v.total_kwh for k, v in rows.items()},
                         {"BLD-A": 4.5, "BLD-B": 3.0, "BLD-C": 1.25})
        self.assertEqual(self.app.rollup_store.quarantined("2026-10-13"), {})
        self.assertEqual(fixed.reconcile(DAY), [])

    def test_recovery_is_idempotent(self):
        fixed = batch(self.app)
        fixed.recover(DAY, ["BLD-B", "BLD-C"])
        fixed.recover(DAY, ["BLD-B", "BLD-C"])
        count = self.app.conn.execute(
            "SELECT COUNT(*) FROM daily_rollups WHERE day = '2026-10-13'").fetchone()[0]
        self.assertEqual(count, 3)
        self.assertEqual(fixed.reconcile(DAY), [])

    def test_nothing_to_recover_is_a_noop(self):
        self.assertEqual(batch(self.app).recover(DAY, []).published, [])


class Retention(unittest.TestCase):
    def test_recovery_refused_outside_49_day_retention(self):
        app = app_with_three_buildings()
        old = RollupBatch(app.batch.energy, app.rollup_store, lambda: date(2026, 12, 1))
        self.assertEqual((date(2026, 12, 1) - DAY).days, 49)
        with self.assertRaises(RetentionExceeded):
            old.recover(DAY, ["BLD-A"])
        self.assertEqual(app.rollup_store.published("2026-10-13"), {})

    def test_day_48_is_still_recoverable(self):
        app = app_with_three_buildings()
        b = RollupBatch(app.batch.energy, app.rollup_store, lambda: date(2026, 11, 30))
        self.assertEqual(b.recover(DAY, ["BLD-A"]).published, ["BLD-A"])


if __name__ == "__main__":
    unittest.main()
