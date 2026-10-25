"""Partitioned daily rollup batch with fault isolation and partial recovery.

Architecture incident of AD-023: a batch job processes part of the data
wrongly; the system must isolate the fault and recover WITHOUT re-running
everything. Design:

* Partition = (building_id, day). Each partition is computed and committed
  on its own; an exception or invariant violation quarantines only that
  partition and the last good published value is kept.
* reconcile(day) recomputes from source readings and lists partitions whose
  published value is wrong, missing or quarantined (detects silent errors).
* recover(day, buildings) re-runs only the listed partitions. Readings are
  kept 49 days, so recovery is refused for older days.

Invariant (domain + DB): a published total is finite, >= 0, there is at most
one published value per partition, and after reconcile() it equals the sum
of valid source readings of that partition.
"""

import itertools
import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from ad023.core.ports import EnergyQueryPort, RollupStorePort, Window, round_kwh

RETENTION_DAYS = 49


class RollupInvariantError(ValueError):
    pass


class RetentionExceeded(ValueError):
    pass


@dataclass
class RunReport:
    run_id: str
    day: str
    published: list = field(default_factory=list)
    quarantined: dict = field(default_factory=dict)


def _identity(building_id, kwh):
    return kwh


class RollupBatch:
    def __init__(self, energy: EnergyQueryPort, store: RollupStorePort, today,
                 transform=_identity, run_ids=None):
        self.energy = energy
        self.store = store
        self.today = today            # callable -> date (injected clock)
        self.transform = transform    # computation step; seam for fault injection
        self._ids = run_ids or (f"run-{n}" for n in itertools.count(1))

    def _check_retention(self, day: date):
        if (self.today() - day).days >= RETENTION_DAYS:
            raise RetentionExceeded(
                f"{day} is outside the {RETENTION_DAYS}-day retention; source readings are gone")

    @staticmethod
    def _window(day: date):
        return Window(f"{day.isoformat()}T00:00:00Z",
                      f"{(day + timedelta(days=1)).isoformat()}T00:00:00Z")

    def execute(self, day: date, buildings=None) -> RunReport:
        self._check_retention(day)
        report = RunReport(next(self._ids), day.isoformat())
        for building_id in sorted(buildings or self.energy.building_ids()):
            try:
                total = self.energy.building_energy(building_id, self._window(day))
                kwh = self.transform(building_id, total.kwh)
                if not isinstance(kwh, (int, float)) or not math.isfinite(kwh) or kwh < 0:
                    raise RollupInvariantError(f"invalid total {kwh!r}")
                self.store.publish(building_id, report.day, report.run_id,
                                   round_kwh(kwh), total.reading_count)
                report.published.append(building_id)
            except Exception as exc:  # isolate: one partition never stops the batch
                self.store.quarantine(building_id, report.day, report.run_id,
                                      f"{type(exc).__name__}: {exc}")
                report.quarantined[building_id] = type(exc).__name__
        return report

    def reconcile(self, day: date) -> list:
        """Partitions whose published value differs from the source, or is missing."""
        key = day.isoformat()
        published = self.store.published(key)
        quarantined = self.store.quarantined(key)
        bad = []
        for building_id in self.energy.building_ids():
            source = self.energy.building_energy(building_id, self._window(day))
            row = published.get(building_id)
            if (building_id in quarantined or row is None
                    or row.total_kwh != round_kwh(source.kwh)
                    or row.reading_count != source.reading_count):
                bad.append(building_id)
        return bad

    def recover(self, day: date, buildings) -> RunReport:
        if not buildings:
            return RunReport("noop", day.isoformat())
        return self.execute(day, buildings)
