"""Reporting module: daily energy totals per building.

Uses the same EnergyQueryPort and rounding as the Dashboard, so the two
cannot drift apart (P2 resolved in C2)."""

from datetime import date, timedelta

from ad023.core.ports import EnergyQueryPort, Window, round_kwh


class DailyRollupJob:
    def __init__(self, energy: EnergyQueryPort):
        self.energy = energy

    def run(self, day: date):
        window = Window(f"{day.isoformat()}T00:00:00Z",
                        f"{(day + timedelta(days=1)).isoformat()}T00:00:00Z")
        return {b: round_kwh(t.kwh) for b, t in self.energy.energy_by_building(window).items()}
