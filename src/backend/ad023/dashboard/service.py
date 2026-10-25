"""Dashboard module. Depends only on ad023.core abstractions.

P1/P2 resolved in C2 (port + single aggregation rule). P3 (no authorization,
raw payload exposure) is still present and is fixed in C4."""

from datetime import datetime

from ad023.core.ports import UNITS, EnergyQueryPort, Window, round_kwh

LATE_AFTER_SECONDS = 300  # [ĐỀ XUẤT] from MQTT draft PR #10, not approved
_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _seconds_between(earlier, later):
    return (datetime.strptime(later, _FMT) - datetime.strptime(earlier, _FMT)).total_seconds()


class DashboardService:
    def __init__(self, energy: EnergyQueryPort):
        self.energy = energy

    def get_building_overview(self, building_id, start, end):
        window = Window(start, end)
        total = self.energy.building_energy(building_id, window)
        return {
            "building_id": building_id,
            "metric": "energy_kwh",
            "unit": UNITS["energy_kwh"],
            "window": {"start": start, "end": end},
            "value": round_kwh(total.kwh),
            "reading_count": total.reading_count,
            "raw_debug_records": self.energy.recent_raw_payloads(building_id, 5),
        }

    def get_device_history(self, device_id, start, end):
        return [{
            "event_time": r.event_time,
            "received_at": r.received_at,
            "metric": r.metric,
            "value": r.value,
            "unit": UNITS[r.metric],
            "late": _seconds_between(r.event_time, r.received_at) > LATE_AFTER_SECONDS,
        } for r in self.energy.device_readings(device_id, Window(start, end))]
